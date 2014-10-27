__import__("pkg_resources").declare_namespace(__name__)

from glob import glob
from shutil import copy, rmtree
from infi.gevent_utils.os import makedirs, path, remove, listdir, walk, rename, symlink
from infi.execute import execute_assert_success, ExecutionError
from infi.pyutils.lazy import cached_method
from pkg_resources import resource_filename
from pexpect import spawn
from fnmatch import fnmatch
from gevent import sleep
from cjson import encode, decode
from logging import getLogger
from pkg_resources import parse_version

logger = getLogger(__name__)


NAME = r"""(?P<package_name>[a-zA-Z]*[a-zA-Z\-_]+[0-9_]?[a-zA-Z\-_]+[a-zA-Z][0-9]?)"""
VERSION = r"""v?(?P<package_version>(?:[\d+\.]+)(?:-develop|-[0-9\.]+(?:_g[0-9a-f]{7})?|(?:(?:\.post\d+\.|\.\d+\.|-\d+-|-develop-\d+-)g[a-z0-9]{7}))?)"""
PLATFORM = r"""(?P<platform_string>vmware-esx|windows|linux-ubuntu-[a-z]+|linux-redhat-\d|linux-centos-\d|osx-\d+\.\d+|centos.el6|centos.el7|redhat.el6|redhat.el7)"""
ARCHITECTURE = r"""(?P<architecture>x86|x64|x86_OVF10|x86_OVF10_UPDATE_ISO|x86_OVF10_UPDATE_ZIP|x64_OVF_10|x64_OVF_10_UPDATE_ISO|x64_OVF_10_UPDATE_ZIP|x64_dd|i686|x86_64)"""
EXTENSION = r"""(?P<extension>rpm|deb|msi|tar\.gz|ova|iso|zip|img)"""
TEMPLATE = r"""^{}.{}.{}.{}\.{}$"""
FILEPATH = TEMPLATE.format(NAME, VERSION, PLATFORM, ARCHITECTURE, EXTENSION)
PLATFORM_STRING = dict(ova='vmware-esx', img='other', zip='other')
TRANSLATED_ARCHITECTURE = {"x86_64": "x64", "i686": "x86"}
TRANSLATED_PLATFORM = {"centos.el6": "linux-centos-6", "centos.el7": "linux-centos-7",
                       "redhat.el6": "linux-redhat-6", "redhat.el7": "linux-redhat-7"}


def translate_filepath(result_tuple):
    package_name, package_version, platform_string, architecture, extension = result_tuple
    return (package_name, package_version,
            TRANSLATED_PLATFORM.get(platform_string, platform_string),
            TRANSLATED_ARCHITECTURE.get(architecture, architecture),
            extension)


def parse_filepath(filepath):
    """:returns: 5-tuple (package_name, package_version, platform_string, architecture, extension)"""
    from re import match
    filename = path.basename(filepath)
    result = match(FILEPATH, filename)
    if result is None:
        logger.debug("failed to parse {}".format(filename))
        return (None, None, None, None, None)
    group = result.groupdict()
    return translate_filepath((group['package_name'], group['package_version'],
            PLATFORM_STRING.get(group['extension'], group['platform_string']),
            group['architecture'], group['extension']))


class ApplicationRepository(object):
    def __init__(self, base_directory):
        super(ApplicationRepository, self).__init__()
        self.base_directory = base_directory
        self.incoming_directory = path.join(base_directory, 'incoming')
        self.appliances_directory = path.join(base_directory, 'appliances')
        self.appliances_updates_directory = path.join(self.appliances_directory, 'updates')
        self.homedir = path.expanduser("~")

    def add(self, source_path):
        """:returns: list of callables to update metadata"""
        if not path.exists(source_path):
            logger.error("Source path {!r} does not exist".format(source_path))
            return list()
        isdir = path.isdir(source_path)
        if isdir:
            files_to_add = [path.join(source_path, filename)
                            for filename in listdir(source_path)] if isdir else [source_path]
            files_to_add = [filepath for filepath in files_to_add if not path.isdir(filepath)]
        else:
            files_to_add = [source_path]
        if not files_to_add:
            logger.info("Nothing to add")
            return list()
        logger.info("waiting for {!r}".format(files_to_add))
        wait_for_sources_to_stabalize(files_to_add)
        logger.info("adding {!r}".format(files_to_add))
        callables_lists = [self.add_single_file(filepath) for filepath in files_to_add]
        logger.info("processing callbacks: {}".format(callables_lists))
        callables_sets = [set(item) for item in callables_lists]
        return list(set.union(*(tuple(callables_sets))))

    def add_single_file(self, filepath):
        try:
            factory = self.get_factory_for_incoming_distribution(filepath)
            if factory is None:
                self.reject_single_file(filepath)
            else:
                callables = factory(filepath) or []
                if path.exists(filepath):
                    remove(filepath)
                return callables
        except Exception:
            logger.exception("Failed to add {!r} to repository".format(filepath))
        return []

    def reject_single_file(self, filepath):
        logger.error("Rejecting file {!r} due to unsupported file format".format(filepath))
        destination_directory = path.join(self.base_directory, 'rejected')
        if not path.exists(destination_directory):
            makedirs(destination_directory)
        logger.info("Moving {!r} to {!r}".format(filepath, destination_directory))
        copy2(filepath, destination_directory)

    def get_factory_for_incoming_distribution(self, filepath):
        _, _, platform_string, _, _ = parse_filepath(filepath)
        logger.debug("Platform string is {!r}".format(platform_string))
        if platform_string is None:
            return None
        add_package_by_postfix = {'msi': self.add_package__msi,
                                  'rpm': self.add_package__rpm,
                                  'deb': self.add_package__deb,
                                  'gz': self.add_package__archives,
                                  'zip': self.add_package__archives,
                                  'ova': self.add_package__ova,
                                  'iso': self.add_package__ova,
                                  'img': self.add_package__img}
        extension = path.splitext(filepath)[1][1:]
        factory = add_package_by_postfix[extension]
        return factory


    def add_package__deb(self, filepath):
        package_name, package_version, platform_string, architecture, extension = parse_filepath(filepath)
        _, distribution_name, codename = platform_string.split('-')
        destination_directory = path.join(self.base_directory, 'deb', distribution_name, 'dists', codename,
                                          'main', 'binary-i386' if architecture == 'x86' else 'binary-amd64')
        if not path.exists(destination_directory):
            makedirs(destination_directory)
        self.sign_deb_package(filepath)
        logger.info("Moving {!r} to {!r}".format(filepath, destination_directory))
        copy2(filepath, destination_directory)
        return [self._prepare_callback(self.update_metadata_for_apt_repositories, destination_directory),
                self.get_update_metadata_for_views_callback()]

    def add_package__rpm(self, filepath):
        package_name, package_version, platform_string, architecture, extension = parse_filepath(filepath)
        _, distribution_name, major_version = platform_string.split('-')
        destination_directory = path.join(self.base_directory, 'rpm', distribution_name, major_version,
                                          'i686' if architecture == 'x86' else 'x86_64')
        if not path.exists(destination_directory):
            makedirs(destination_directory)
        self.sign_rpm_package(filepath)
        logger.info("Moving {!r} to {!r}".format(filepath, destination_directory))
        copy2(filepath, destination_directory)
        return [self._prepare_callback(self.update_metadata_for_yum_repositories, destination_directory),
                self.get_update_metadata_for_views_callback()]

    def add_package__msi(self, filepath):
        package_name, package_version, platform_string, architecture, extension = parse_filepath(filepath)
        destination_directory = path.join(self.base_directory, 'msi', architecture)
        if not path.exists(destination_directory):
            makedirs(destination_directory)
        logger.info("Moving {!r} to {!r}".format(filepath, destination_directory))
        copy2(filepath, destination_directory)
        return [self.get_update_metadata_for_views_callback()]

    def add_package__archives(self, filepath):
        if 'vmware-esx' in filepath:
            return self.add_package__ova(filepath)
        package_name, package_version, platform_string, architecture, extension = parse_filepath(filepath)
        destination_directory = path.join(self.base_directory, 'archives')
        if filepath.lower().startswith("python"):
            destination_directory = path.join(self.base_directory, 'python')
        if not path.exists(destination_directory):
            makedirs(destination_directory)
        logger.info("Moving {!r} to {!r}".format(filepath, destination_directory))
        copy2(filepath, destination_directory)

    def add_package__ova(self, filepath):
        package_name, package_version, platform_string, architecture, extension = parse_filepath(filepath)
        destination_directory = path.join(self.base_directory, 'ova')
        if not path.exists(destination_directory):
            makedirs(destination_directory)
        logger.info("Moving {!r} to {!r}".format(filepath, destination_directory))
        copy2(filepath, destination_directory)
        return [self._prepare_callback(self.update_metadata_for_views)]

    def add_package__img(self, filepath):
        package_name, package_version, platform_string, architecture, extension = parse_filepath(filepath)
        destination_directory = path.join(self.base_directory, 'img')
        if not path.exists(destination_directory):
            makedirs(destination_directory)
        logger.info("Moving {!r} to {!r}".format(filepath, destination_directory))
        copy2(filepath, destination_directory)
        return [self._prepare_callback(self.update_metadata_for_views)]

    def update_metadata(self):
        self.update_metadata_for_views()
        self.update_metadata_for_yum_repositories()
        self.update_metadata_for_apt_repositories()

# TODO
# * Replace the metadata json file with redis
