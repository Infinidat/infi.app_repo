__import__("pkg_resources").declare_namespace(__name__)

from glob import glob
from shutil import copy2
from os import makedirs, path, remove, listdir, pardir
from infi.execute import execute_assert_success, ExecutionError
from pkg_resources import resource_filename
from time import sleep
from logging import getLogger

logger = getLogger(__name__)

def log_execute_assert_success(args):
    logger.info("Executing {}".format(' '.join(args)))
    return execute_assert_success(args)

def is_file_open(filepath):
    return log_execute_assert_success(['lsof', filepath]).get_stdout() != ''

def wait_for_directory_to_stabalize(source_path):
    if not path.isdir(source_path):
        return
    while True:
        items = [path.join(source_path, filename) for filename in listdir(source_path)]
        files = [item for item in items if path.isdir(item)]
        if any([is_file_open(filepath) for filepath in files]):
            sleep(1)
            continue
        break

NAME = r"""(?P<package_name>[a-z][a-z\-]+[a-z])"""
VERSION = r"""(?P<package_version>(?:\d|\d\.\d|\d\.\d.\d)(?:|-develop-\d+-g[a-z0-9]{7}))"""
PLATFORM = r"""(?P<platform_string>windows|linux-ubuntu-[a-z]+|linux-redhat-\d|linux-centos-\d)"""
ARCHITECTURE = r"""(?P<architecture>x86|x64)"""
EXTENSION = r"""(?P<extension>rpm|deb|msi|tar\.gz)"""
TEMPLATE = r"""^{}-{}-{}-{}\.{}$"""
FILEPATH = TEMPLATE.format(NAME, VERSION, PLATFORM, ARCHITECTURE, EXTENSION)

def parse_filepath(filepath):
    """:returns: 5-tuple (package_name, package_version, platform_string, architecture, extension)"""
    from re import match
    result = match(FILEPATH, path.basename(filepath))
    if result is None:
        return (None, None, None, None, None)
    group = result.groupdict()
    return (group['package_name'], group['package_version'],
            group['platform_string'], group['architecture'],
            group['extension'])

class ApplicationRepository(object):
    def __init__(self, base_directory):
        super(ApplicationRepository, self).__init__()
        self.base_directory = base_directory
        self.incoming_directory = path.join(base_directory, 'incoming')

    def initialize(self):
        if not path.exists(self.base_directory):
            makedirs(self.base_directory)
        if not path.exists(self.incoming_directory):
            makedirs(self.incoming_directory)
    
    def is_upload_user_exists(self):
        try:
            log_execute_assert_success(['id', 'app_repo'])
        except ExecutionError:
            return False
        return True

    def create_upload_user(self):
        if self.is_upload_user_exists():
            log_execute_assert_success(['deluser', 'app_repo'])
        from passlib.hash import sha256_crypt
        password = sha256_crypt.encrypt("app_repo")
        log_execute_assert_success(['useradd', '--no-create-home', '--no-user-group',
                                    '--shell', '/bin/false', '--home-dir', self.incoming_directory,
                                    '--password', password, 'app_repo'])

    def copy_vsftp_config_file(self):
        src = resource_filename(__name__, 'vsftpd.conf')
        copy2(src, '/etc/')

    def restart_vsftpd(self):
        log_execute_assert_success(['service', 'vsftpd', 'restart'])

    def fix_permissions(self):
        parent = self.base_directory
        while True:
            parent = path.abspath(path.join(parent, pardir))
            log_execute_assert_success(['chmod', '755', parent])
            if parent in ['/', '']:
                break
        log_execute_assert_success(['chmod', '-Rf', '755', self.base_directory])
        log_execute_assert_success(['chown', '-R', 'app_repo', self.incoming_directory])

    def setup(self):
        self.initialize()
        self.create_upload_user()
        self.fix_permissions()
        self.copy_vsftp_config_file()
        self.restart_vsftpd()

    def add(self, source_path):
        if not path.exists(source_path):
            logger.error("Source path {!r} does not exist".format(source_path))
            return
        isdir = path.isdir(source_path)
        if isdir:
                wait_for_directory_to_stabalize(source_path)
        files_to_add = [path.join(source_path, filename)
                        for filename in listdir(source_path)] if isdir else [source_path]
        if not files_to_add:
            logger.info("Nothing to add")
            return
        for filepath in files_to_add:
            self.add_single_file(filepath)
        self.update_metadata()

    def add_single_file(self, filepath):
        try:
            factory = self.get_factory_for_incoming_distribution(filepath)
            if factory is None:
                logger.error("Rejecting file {!r} due to unsupported file format".format(filepath))
            else:
                factory(filepath)
        except Exception:
            logger.exception("Failed to add {!r} to repository".format(filepath))
        finally:
            pass
            #remove(filepath)

    def get_factory_for_incoming_distribution(self,filepath):
        _, _, platform_string, _, _ = parse_filepath(filepath)
        logger.debug("Platform string is {!r}".format(platform_string))
        if platform_string is None:
            return None
        add_package_by_platfrom_prefix = {'windows': self.add_package_for_windows,
                                          'linux-redhat': self.add_package_for_redhat,
                                          'linux-centos': self.add_package_for_centos,
                                          'linux-ubuntu': self.add_package_for_ubuntu,
                                         }
        [factory] = [value for key, value in add_package_by_platfrom_prefix.items()
                     if platform_string.startswith(key)]
        return factory

    def add_package_for_apt_repository(self, filepath):
        package_name, package_version, platform_string, architecture, extension = parse_filepath(filepath)
        _, distribution_name, codename = platform_string.split('-')
        destination_directory = path.join(self.base_directory, 'deb', distribution_name, 'dists', codename,
                                         'main', 'binary-i386' if architecture == 'x86' else 'binary-amd64')
        if not path.exists(destination_directory):
            makedirs(destination_directory)
        logger.info("Copying {!r} to {!r}".format(filepath, destination_directory))
        copy2(filepath, destination_directory)

    def add_package_for_ubuntu(self, filepath):
        return self.add_package_for_apt_repository(filepath)

    def add_package_for_yum_repository(self, filepath):
        package_name, package_version, platform_string, architecture, extension = parse_filepath(filepath)
        _, distribution_name, major_version = platform_string.split('-')
        destination_directory = path.join(self.base_directory, 'rpm', distribution_name, major_version,
                                          'i386' if architecture == 'x86' else 'x86_64')
        if not path.exists(destination_directory):
            makedirs(destination_directory)
        logger.info("Copying {!r} to {!r}".format(filepath, destination_directory))
        copy2(filepath, destination_directory)

    def add_package_for_redhat(self, filepath):
        self.add_package_for_yum_repository(filepath)

    def add_package_for_centos(self, filepath):
        self.add_package_for_yum_repository(filepath)

    def add_package_for_windows(self, filepath):
        package_name, package_version, platform_string, architecture, extension = parse_filepath(filepath)
        destination_directory = path.join(self.base_directory, 'msi', architecture)
        if not path.exists(destination_directory):
            makedirs(destination_directory)
        logger.info("Copying {!r} to {!r}".format(filepath, destination_directory))
        copy2(filepath, destination_directory)

    def update_metadata(self):
        self.update_metadata_for_views()
        self.update_metadata_for_yum_repositories()
        self.update_metadata_for_apt_repositories()

    def update_metadata_for_views(self):
        # TODO NotImplementedError
        pass

    def update_metadata_for_yum_repositories(self):
        for dirpath in glob(path.join(self.base_directory, 'rpm', '*', '*', '*')):
            if not path.isdir(dirpath):
                continue
            if path.exists(path.join(dirpath, 'repodata')):
                log_execute_assert_success(['createrepo', '--update', dirpath])
            else:
                log_execute_assert_success(['createrepo', dirpath])

    def update_metadata_for_apt_repositories(self):
        from gzip import open
        for dirpath in glob(path.join(self.base_directory, 'deb', '*', 'dists', '*', 'main', 'binary-*')):
           if not path.isdir(dirpath):
               continue
           base, deb, distribution_name, dists, codename, main, binary = dirpath.rsplit('/', 6)
           packages_gz = path.join(dirpath, 'Packages.gz')
           pid = log_execute_assert_success(['dpkg-scanpackages', dirpath, '/dev/null'])
           content = pid.get_stdout()
           ftp_base = path.join(base, deb, distribution_name)
           content = content.replace(ftp_base + '/', '')
           package_gz_fd = open(packages_gz, 'wb')
           package_gz_fd.write(content)
           package_gz_fd.close()

