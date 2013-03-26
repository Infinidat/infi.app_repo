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

GPG_FILENAMES = ['gpg.conf', 'pubring.gpg', 'random_seed', 'secring.gpg', 'trustdb.gpg']

RELEASE_FILE_HEADER = "Codename: {}\nArchitectures: am64 i386\nComponents: main"
RPMDB_PATH = "/var/lib/rpm"

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
VERSION = r"""v?(?P<package_version>(?:[\d\.]+)(?:-develop|(?:(?:\.post\d+\.|-\d+-|-develop-\d+-)g[a-z0-9]{7}))?)"""
PLATFORM = r"""(?P<platform_string>windows|linux-ubuntu-[a-z]+|linux-redhat-\d|linux-centos-\d|osx-\d+\.\d+)"""
ARCHITECTURE = r"""(?P<architecture>x86|x64|x86_OVF10|x64_OVF_10)"""
EXTENSION = r"""(?P<extension>rpm|deb|msi|tar\.gz|ova|iso|zip)"""
TEMPLATE = r"""^{}-{}-{}-{}\.{}$"""
FILEPATH = TEMPLATE.format(NAME, VERSION, PLATFORM, ARCHITECTURE, EXTENSION)

def parse_filepath(filepath):
    """:returns: 5-tuple (package_name, package_version, platform_string, architecture, extension)"""
    from re import match
    filename = path.basename(filepath)
    result = match(FILEPATH, filename)
    if result is None:
        logger.debug("failed to parse {}".format(filename))
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
        self.homedir = path.expanduser("~")

    def initialize(self):
        for required_path in [self.base_directory,
                              self.incoming_directory,
                              self.appliances_directory,
                              self.appliances_updates_directory]:
            if not path.exists(required_path):
                makedirs(required_path)

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

    def install_upstart_script_for_webserver(self):
        from infi.app_repo.upstart import install_webserver, install_worker, install_watchdog
        services = ['app_repo_webserver', 'app_repo_worker']
        for service in services:
            log_execute_assert_success(["service", service, "stop"], True)
        install_webserver(self.base_directory)
        install_worker(self.base_directory)
        install_watchdog(self.base_directory)
        for service in services:
            log_execute_assert_success(["service", service, "start"], True)

    def fix_entropy_generator(self):
        log_execute_assert_success(['/etc/init.d/rng-tools', 'stop'], True)
        with open("/etc/default/rng-tools", 'a') as fd:
            fd.write("HRNGDEVICE=/dev/urandom\n")
        log_execute_assert_success(['/etc/init.d/rng-tools', 'start'], True)

    def generate_gpg_key_if_does_not_exist(self):
        """:returns: True if the gpg key existed before"""
        self.fix_entropy_generator()
        gnupg_directory = path.join(self.homedir, ".gnupg")
        if all([path.exists(path.join(gnupg_directory, filename)) for filename in GPG_FILENAMES]):
            return True
        rmtree(gnupg_directory, ignore_errors=True)
        log_execute_assert_success(['gpg', '--batch', '--gen-key',
                                   resource_filename(__name__, 'gpg_batch_file')])
        pid = log_execute_assert_success(['gpg', '--export', '--armor'])
        with open(path.join(self.homedir, ".rpmmacros"), 'w') as fd:
            fd.write(GPG_TEMPLATE)
        with open(path.join(self.homedir, 'gpg.key'), 'w') as fd:
            fd.write(pid.get_stdout())
        return False

    def import_gpg_key_to_rpm_database(self):
        key = path.join(self.homedir, 'gpg.key')
        log_execute_assert_success(['rpm', '--import', key])

    def sign_all_existing_deb_and_rpm_packages(self):
        # this is necessary because we replaced the gpg key
        for filepath in find_files(path.join(self.base_directory, 'rpm'), '*.rpm'):
            self.sign_rpm_package(filepath)
        for filepath in find_files(path.join(self.base_directory, 'deb'), '*.deb'):
            self.sign_deb_package(filepath)

    def set_write_permissions_on_incoming_directory(self):
        from os import chown
        from pwd import getpwnam
        pwnam = getpwnam("app_repo")
        chown(self.incoming_directory, pwnam.pw_uid, pwnam.pw_gid)

    def setup(self):
        self.initialize()
        self.write_configuration_file()
        self.create_upload_user()
        self.copy_vsftp_config_file()
        self.restart_vsftpd()
        self.install_upstart_script_for_webserver()
        if not self.generate_gpg_key_if_does_not_exist():
            self.import_gpg_key_to_rpm_database()
            self.sign_all_existing_deb_and_rpm_packages()
            self.update_metadata()
        self.set_write_permissions_on_incoming_directory()

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
        return any(self.add_single_file(filepath) for filepath in files_to_add)

    def add_single_file(self, filepath):
        try:
            factory = self.get_factory_for_incoming_distribution(filepath)
            if factory is None:
                logger.error("Rejecting file {!r} due to unsupported file format".format(filepath))
            else:
                factory(filepath)
                remove(filepath)
                return True
        except Exception:
            logger.exception("Failed to add {!r} to repository".format(filepath))
        return False

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

    def sign_deb_package(self, filepath):
        logger.info("Signing {!r}".format(filepath))
        log_execute_assert_success(['dpkg-sig', '--sign', 'builder', filepath])

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

    def sign_rpm_package(self, filepath):
        logger.info("Signing {!r}".format(filepath))
        command = ['rpm', '--addsign', filepath]
        logger.debug("Spawning {}".format(command))
        pid = spawn(command[0], command[1:], timeout=120)
        logger.debug("Waiting for passphrase request")
        pid.expect("Enter pass phrase:")
        pid.sendline("\n")
        logger.debug("Passphrase entered, waiting for rpm to exit")
        pid.wait() if pid.isalive() else None
        assert pid.exitstatus == 0
        # execute_assert_success(['rpm', '-vv', '--checksig', filepath])

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

    def _write_packages_gz_file(self, dirpath, ftp_base):
        import gzip
        cache = path.join(self.incoming_directory, "apt_cache.db")
        # pid = log_execute_assert_success(['apt-ftparchive', '--db', cache, 'packages', dirpath])
        pid = log_execute_assert_success(['dpkg-scanpackages', dirpath, '/dev/null'])
        content = pid.get_stdout()
        content = content.replace(ftp_base + '/', '')
        packages = path.join(dirpath, 'Packages')
        with open(packages, 'w') as fd:
            fd.write(content)
        fd = gzip.open(packages + '.gz', 'wb')
        fd.write(content)
        fd.close()

    def _write_release_file(self, dirpath, ):
        base, deb, distribution_name, dists, codename = dirpath.rsplit('/', 4)
        cache = path.join(self.incoming_directory, "apt_cache.db")
        pid = log_execute_assert_success(['apt-ftparchive', '--db', cache, 'release', dirpath])
        content = pid.get_stdout()
        release = path.join(dirpath, 'Release')
        with open(release, 'w') as fd:
            fd.write((RELEASE_FILE_HEADER + "\n{}").format(codename, content))
        in_release = path.join(dirpath, 'InRelease')
        release_gpg = path.join(dirpath, 'Release.gpg')
        for filepath in [in_release, release_gpg]:
            if path.exists(filepath):
                remove(filepath)
        log_execute_assert_success(['gpg', '--clearsign', '-o', in_release, release])
        log_execute_assert_success(['gpg', '-abs', '-o', release_gpg, release])

    def update_metadata_for_apt_repositories(self):
        for dirpath in glob(path.join(self.base_directory, 'deb', '*', 'dists', '*', 'main', 'binary-*')):
            if not path.isdir(dirpath):
                continue
            base, deb, distribution_name, dists, codename, main, binary = dirpath.rsplit('/', 6)
            ftp_base = path.join(base, deb, distribution_name)
            self._write_packages_gz_file(dirpath, ftp_base)
        for dirpath in glob(path.join(self.base_directory, 'deb', '*', 'dists', '*')):
            if not path.isdir(dirpath):
                continue
            self._write_release_file(dirpath)

    def get_views_metadata(self):
        filepath = path.join(self.base_directory, 'metadata.json')
        if not path.exists(filepath):
            return dict(packages=())
        with open(filepath) as fd:
            return decode(fd.read())

    def write_configuration_file(self):
        from infi.execute import execute_assert_success
        from .config import get_projectroot
        app_repo = path.join(get_projectroot(), 'bin', 'app_repo')
        execute_assert_success("{} dump defaults > /etc/app_repo.conf".format(app_repo), shell=True)

# TODO
# * Replace the metadata json file with redis
