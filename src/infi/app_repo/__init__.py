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
