__import__("pkg_resources").declare_namespace(__name__)

from glob import glob
from shutil import copy2, rmtree
from os import makedirs, path, remove, listdir, pardir, walk
from infi.execute import execute_assert_success, ExecutionError
from pkg_resources import resource_filename
from pexpect import spawn
from fnmatch import fnmatch
from time import sleep
from cjson import encode, decode
from logging import getLogger
from pkg_resources import parse_version

logger = getLogger(__name__)

GPG_TEMPLATE = """
%_signature gpg
%_gpg_name  app_repo
%__gpg_sign_cmd %{__gpg} \
    gpg --force-v3-sigs --digest-algo=sha1 --batch --no-verbose --no-armor \
    --passphrase-fd 3 --no-secmem-warning -u "%{_gpg_name}" \
    -sbo %{__signature_filename} %{__plaintext_filename}
"""

SUDO_PREFIX = ['sudo', '-H', '-u', 'app_repo']
GPG_FILENAMES = ['gpg.conf', 'pubring.gpg', 'random_seed', 'secring.gpg', 'trustdb.gpg']

def log_execute_assert_success(args, allow_to_fail=False):
    logger.info("Executing {}".format(' '.join(args)))
    try:
        return execute_assert_success(args)
    except ExecutionError:
        logger.exception("Execution failed")
        if not allow_to_fail:
            raise

def is_file_open(filepath):
    return log_execute_assert_success(['lsof', filepath]).get_stdout() != ''

def find_files(directory, pattern):
    for root, dirs, files in walk(directory):
        for basename in files:
            if fnmatch(basename, pattern):
                filename = path.join(root, basename)
                yield filename

def wait_for_directory_to_stabalize(source_path):
    if path.isdir(source_path):
        return
    while True:
        items = [path.join(source_path, filename) for filename in listdir(source_path)]
        files = [item for item in items if path.isdir(item)]
        if any([is_file_open(filepath) for filepath in files]):
            sleep(1)
            continue
        break

NAME = r"""(?P<package_name>[a-z][a-z\-]+[a-z])"""
VERSION = r"""v?(?P<package_version>(?:[\d\.]+)(?:|-develop|-develop-\d+-g[a-z0-9]{7}))"""
PLATFORM = r"""(?P<platform_string>windows|linux-ubuntu-[a-z]+|linux-redhat-\d|linux-centos-\d|osx-\d+\.\d+)"""
ARCHITECTURE = r"""(?P<architecture>x86|x64|x86_OVF10|x64_OVF_10)"""
EXTENSION = r"""(?P<extension>rpm|deb|msi|tar\.gz|ova|iso|zip)"""
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
            group['platform_string'] if group['extension'] != 'ova' else 'vmware-esx',
            group['architecture'], group['extension'])

class ApplicationRepository(object):
    def __init__(self, base_directory):
        super(ApplicationRepository, self).__init__()
        self.base_directory = base_directory
        self.incoming_directory = path.join(base_directory, 'incoming')
        self.appliances_directory = path.join(base_directory, 'appliances')
        self.appliances_updates_directory = path.join(self.appliances_directory, 'updates')

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
                                    '--shell', '/bin/sh', '--home-dir', self.incoming_directory,
                                    '--password', password, 'app_repo'])

    def copy_vsftp_config_file(self):
        src = resource_filename(__name__, 'vsftpd.conf')
        with open(src) as fd:
            content = fd.read()
        with open('/etc/vsftpd.conf', 'w') as fd:
            fd.write(content.replace("anon_root=", "anon_root={}".format(self.base_directory)))

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
        log_execute_assert_success(['chown', '-R', 'app_repo', self.base_directory])

    def set_cron_job(self):
        from crontab import CronTab
        from infi.app_repo.scripts import PROJECT_DIRECTORY
        crontab = CronTab("app_repo")
        crontab.lines = []
        command = crontab.new('{} > /dev/null 2>&1 '.format(path.join(PROJECT_DIRECTORY, 'bin', 'process_incoming')))
        command.minute.every(10)
        crontab.write()

    def install_upstart_script_for_webserver(self):
        from infi.app_repo.upstart import install
        log_execute_assert_success(["initctl", "stop", "app_repo"], True)
        install()
        log_execute_assert_success(["initctl", "start", "app_repo"], True)

    def fix_entropy_generator(self):
        log_execute_assert_success(['/etc/init.d/rng-tools', 'stop'], True)
        with open("/etc/default/rng-tools", 'a') as fd:
            fd.write("HRNGDEVICE=/dev/urandom\n")
        log_execute_assert_success(['/etc/init.d/rng-tools', 'start'], True)

    def generate_gpg_key_if_does_not_exist(self):
        self.fix_entropy_generator()
        gnupg_directory = path.join(self.incoming_directory, ".gnupg")
        if all([path.exists(path.join(gnupg_directory, filename)) for filename in GPG_FILENAMES]):
            return
        rmtree(gnupg_directory, ignore_errors=True)
        log_execute_assert_success(SUDO_PREFIX + ['gpg', '--batch', '--gen-key',
                                   resource_filename(__name__, 'gpg_batch_file')])
        pid = log_execute_assert_success(SUDO_PREFIX + ['gpg', '--export', '--armor'])
        with open(path.join(self.incoming_directory, ".rpmmacros"), 'w') as fd:
            fd.write(GPG_TEMPLATE)
        with open(path.join(self.base_directory, 'gpg.key'), 'w') as fd:
            fd.write(pid.get_stdout())

    def import_gpg_key_to_rpm_database(self):
        key = path.join(self.base_directory, 'gpg.key')
        for prefix in [[], SUDO_PREFIX]:
            log_execute_assert_success(prefix + ['rpm', '--import', key])


    def sign_all_existing_deb_and_rpm_packages(self):
        # this is necessary because we replaced the gpg key
        for filepath in find_files(path.join(self.base_directory, 'rpm'), '*.rpm'):
            self.sign_rpm_package(filepath, sudo=True)
        for filepath in find_files(path.join(self.base_directory, 'deb'), '*.deb'):
            self.sign_deb_package(filepath, sudo=True)

    def setup(self):
        self.initialize()
        self.create_upload_user()
        self.fix_permissions()
        self.copy_vsftp_config_file()
        self.restart_vsftpd()
        self.set_cron_job()
        self.install_upstart_script_for_webserver()
        self.generate_gpg_key_if_does_not_exist()
        self.import_gpg_key_to_rpm_database()
        self.sign_all_existing_deb_and_rpm_packages()
        self.update_metadata()

    def add(self, source_path):
        """:returns: True if metadata was updates"""
        if not path.exists(source_path):
            logger.error("Source path {!r} does not exist".format(source_path))
            return False
        isdir = path.isdir(source_path)
        if isdir:
            wait_for_directory_to_stabalize(source_path)
        files_to_add = [path.join(source_path, filename)
                        for filename in listdir(source_path)] if isdir else [source_path]
        files_to_add = [filepath for filepath in files_to_add if not path.isdir(filepath)]
        if not files_to_add:
            logger.info("Nothing to add")
            return False
        for filepath in files_to_add:
            self.add_single_file(filepath)
        self.update_metadata()
        return True

    def add_single_file(self, filepath):
        try:
            factory = self.get_factory_for_incoming_distribution(filepath)
            if factory is None:
                logger.error("Rejecting file {!r} due to unsupported file format".format(filepath))
            else:
                factory(filepath)
                remove(filepath)
        except Exception:
            logger.exception("Failed to add {!r} to repository".format(filepath))

    def get_factory_for_incoming_distribution(self,filepath):
        _, _, platform_string, _, _ = parse_filepath(filepath)
        logger.debug("Platform string is {!r}".format(platform_string))
        if platform_string is None:
            return None
        add_package_by_postfix = {'msi': self.add_package__msi,
                                          'rpm': self.add_package__rpm,
                                          'deb': self.add_package__deb,
                                          'tar.gz': self.add_package__archives,
                                          'zip': self.add_package__archives,
                                          'ova': self.add_package__ova
                                         }
        [factory] = [value for key, value in add_package_by_postfix.items()
                     if filepath.endswith(key)]
        return factory

    def sign_deb_package(self, filepath, sudo=False):
        logger.info("Signing {!r}".format(filepath))
        prefix = SUDO_PREFIX if sudo else []
        log_execute_assert_success(prefix + ['dpkg-sig', '--sign', 'builder', filepath])

    def add_package__deb(self, filepath):
        package_name, package_version, platform_string, architecture, extension = parse_filepath(filepath)
        _, distribution_name, codename = platform_string.split('-')
        destination_directory = path.join(self.base_directory, 'deb', distribution_name, 'dists', codename,
                                         'main', 'binary-i386' if architecture == 'x86' else 'binary-amd64')
        if not path.exists(destination_directory):
            makedirs(destination_directory)
        self.sign_deb_package(filepath)
        logger.info("Copying {!r} to {!r}".format(filepath, destination_directory))
        copy2(filepath, destination_directory)

    def sign_rpm_package(self, filepath, sudo=False):
        logger.info("Signing {!r}".format(filepath))
        prefix = SUDO_PREFIX if sudo else []
        command = prefix + ['rpm', '--addsign', filepath]
        logger.debug("Spawning {}".format(command))
        pid = spawn(command[0], command[1:], timeout=120)
        logger.debug("Waiting for passphrase request")
        pid.expect("Enter pass phrase:")
        pid.sendline("\n")
        logger.debug("Passphrase entered, waiting for rpm to exit")
        pid.wait() if pid.isalive() else None
        assert pid.exitstatus == 0
        execute_assert_success(prefix + ['rpm', '-vv', '--checksig', filepath])

    def add_package__rpm(self, filepath):
        package_name, package_version, platform_string, architecture, extension = parse_filepath(filepath)
        _, distribution_name, major_version = platform_string.split('-')
        destination_directory = path.join(self.base_directory, 'rpm', distribution_name, major_version,
                                          'i686' if architecture == 'x86' else 'x86_64')
        if not path.exists(destination_directory):
            makedirs(destination_directory)
        self.sign_rpm_package(filepath)
        logger.info("Copying {!r} to {!r}".format(filepath, destination_directory))
        copy2(filepath, destination_directory)

    def add_package__msi(self, filepath):
        package_name, package_version, platform_string, architecture, extension = parse_filepath(filepath)
        destination_directory = path.join(self.base_directory, 'msi', architecture)
        if not path.exists(destination_directory):
            makedirs(destination_directory)
        logger.info("Copying {!r} to {!r}".format(filepath, destination_directory))
        copy2(filepath, destination_directory)

    def add_package__archives(self, filepath):
        package_name, package_version, platform_string, architecture, extension = parse_filepath(filepath)
        destination_directory = path.join(self.base_directory, 'archives')
        if not path.exists(destination_directory):
            makedirs(destination_directory)
        logger.info("Copying {!r} to {!r}".format(filepath, destination_directory))
        copy2(filepath, destination_directory)

    def add_package__ova(self, filepath):
        package_name, package_version, platform_string, architecture, extension = parse_filepath(filepath)
        destination_directory = path.join(self.base_directory, 'ova')
        if not path.exists(destination_directory):
            makedirs(destination_directory)
        logger.info("Copying {!r} to {!r}".format(filepath, destination_directory))
        copy2(filepath, destination_directory)

    def update_metadata(self):
        self.update_metadata_for_views()
        self.update_metadata_for_yum_repositories()
        self.update_metadata_for_apt_repositories()

    def update_metadata_for_views(self):
        packages = list(self.gather_metadata_for_views())
        with open(path.join(self.base_directory, 'metadata.json'), 'w') as fd:
            fd.write(encode(dict(packages=packages)))

    def _exclude_filepath_from_views(self, filepath):
        return filepath.startswith(self.incoming_directory) or \
               path.join("ova", "updates") in filepath or \
               "archives" in filepath

    def gather_metadata_for_views(self):
        all_files =  []
        all_files = [filepath for filepath in find_files(self.base_directory, '*')
                     if not self._exclude_filepath_from_views(filepath)
                     and parse_filepath(filepath) != (None, None, None, None, None)]
        distributions = [parse_filepath(distribution) + (distribution, ) for distribution in all_files]
        package_names = set([distribution[0] for distribution in distributions])
        distributions_by_package = {package_name: [distribution for distribution in distributions
                                                   if distribution[0] == package_name]
                                    for package_name in package_names}
        for package_name, package_distributions in sorted(distributions_by_package.items(),
                                                          key=lambda item: item[0]):
            package_versions = set([distribution[1] for distribution in package_distributions])
            distributions_by_version = {package_version: [dict(platform=distribution[2],
                                                               architecture=distribution[3],
                                                               extension=distribution[4],
                                                               filepath=distribution[5].replace(self.base_directory, ''))
                                                          for distribution in package_distributions
                                                          if distribution[1] == package_version]
                                        for package_version in package_versions}
            yield dict(name=package_name,
                       display_name=' '.join([item.capitalize() for item in package_name.split('-')]),
                       releases=[dict(version=key, distributions=value)
                                 for key, value in sorted(distributions_by_version.items(),
                                                          key=lambda item: parse_version(item[0]),
                                                          reverse=True)])

    def update_metadata_for_yum_repositories(self):
        for dirpath in glob(path.join(self.base_directory, 'rpm', '*', '*', '*')):
            if not path.isdir(dirpath):
                continue
            if path.exists(path.join(dirpath, 'repodata')):
                try:
                    log_execute_assert_success(['createrepo', '--update', dirpath])
                except:
                    logger.exception("Failed to update metadata, will attempt to remove it and create it from scratch")
                    rmtree(path.join(dirpath, 'repodata'), ignore_errors=True)
                    log_execute_assert_success(['createrepo', dirpath])
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

    def get_views_metadata(self):
        with open(path.join(self.base_directory, 'metadata.json')) as fd:
            return decode(fd.read())

