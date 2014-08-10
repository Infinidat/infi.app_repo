__import__("pkg_resources").declare_namespace(__name__)

from glob import glob
from shutil import copy, rmtree
from os import makedirs, path, remove, listdir, walk, rename, symlink
from infi.execute import execute_assert_success, ExecutionError
from infi.pyutils.lazy import cached_method
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
    return filepath in log_execute_assert_success(['lsof']).get_stdout()

def find_files(directory, pattern):
    for root, dirs, files in walk(directory):
        for basename in files:
            if fnmatch(basename, pattern):
                filename = path.join(root, basename)
                yield filename

def is_file_size_changed(file_sizes, filepath):
    from os import stat
    old = file_sizes.get(filepath)
    new = stat(filepath).st_size
    file_sizes[filepath] = new
    return old != new

def wait_for_sources_to_stabalize(sources):
    file_sizes = dict()
    while True:
        if any([is_file_open(filepath) for filepath in sources]):
            sleep(1)
            continue
        if any([is_file_size_changed(file_sizes, filepath) for filepath in sources]):
            sleep(1)
            continue
        break

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


def copy2(source_path, destination_directory):
    destination_path = path.join(destination_directory, path.basename(source_path))
    rename(source_path, destination_path)


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

    def configure_nginx(self):
        config_file = resource_filename(__name__, 'nginx.conf')
        nginx_conf_dir = path.join(path.sep, "etc", "nginx")
        sites_enabled = path.join(nginx_conf_dir, "sites-enabled")
        sites_available = path.join(nginx_conf_dir, "sites-available")
        for filename in glob(path.join(sites_enabled, "*")):
            remove(filename)
        if not path.exists(sites_available):
            makedirs(sites_available)
        if not path.exists(sites_enabled):
            makedirs(sites_enabled)
        with open(config_file) as src, open(path.join(sites_available, "app-repo"), "w") as dst:
                dst.write(src.read())
        symlink(path.join(sites_available, "app-repo"), path.join(sites_enabled, "app-repo"))

    def restart_vsftpd(self):
        log_execute_assert_success(['service', 'vsftpd', 'restart'])

    def restart_nginx(self):
        log_execute_assert_success(['service', 'nginx', 'restart'])

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
        already_generated = all([path.exists(path.join(gnupg_directory, filename)) for filename in GPG_FILENAMES])
        home_key_path = path.join(self.homedir, 'gpg.key')
        already_generated = already_generated and path.exists(home_key_path)
        if not already_generated:
            rmtree(gnupg_directory, ignore_errors=True)
            log_execute_assert_success(['gpg', '--batch', '--gen-key',
                                       resource_filename(__name__, 'gpg_batch_file')])
            pid = log_execute_assert_success(['gpg', '--export', '--armor'])
            with open(path.join(self.homedir, ".rpmmacros"), 'w') as fd:
                fd.write(GPG_TEMPLATE)
            with open(home_key_path, 'w') as fd:
                fd.write(pid.get_stdout())
        data_key_path = path.join(self.base_directory, 'gpg.key')
        if not path.exists(data_key_path):
            copy(home_key_path, data_key_path)
        return already_generated

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
        self.configure_nginx()
        self.restart_vsftpd()
        self.restart_nginx()
        self.install_upstart_script_for_webserver()
        if not self.generate_gpg_key_if_does_not_exist():
            self.import_gpg_key_to_rpm_database()
            self.sign_all_existing_deb_and_rpm_packages()
            self.update_metadata()
        self.set_write_permissions_on_incoming_directory()

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
                logger.error("Rejecting file {!r} due to unsupported file format".format(filepath))
            else:
                callables = factory(filepath) or []
                if path.exists(filepath):
                    remove(filepath)
                return callables
        except Exception:
            logger.exception("Failed to add {!r} to repository".format(filepath))
        return []

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
                                  'img': self.add_package__img,
                                 }
        extension = path.splitext(filepath)[1]
        factory = add_package_by_postfix[extension]
        return factory

    def sign_deb_package(self, filepath):
        logger.info("Signing {!r}".format(filepath))
        log_execute_assert_success(['dpkg-sig', '--sign', 'builder', filepath])

    @cached_method
    def _prepare_callback(self, func, *args, **kwargs):
        return lambda: func(*args, **kwargs)

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
        return [self._prepare_callback(self.update_metadata_for_apt_repositories, destination_directory),
                self.get_update_metadata_for_views_callback()]

    def sign_rpm_package(self, filepath):
        from os import environ
        logger.info("Signing {!r}".format(filepath))
        command = ['rpm', '--addsign', filepath]
        logger.debug("Spawning {}".format(command))
        env = environ.copy()
        env['HOME'] = env.get('HOME', "/root")
        pid = spawn(command[0], command[1:], timeout=120, cwd=self.incoming_directory, env=env)
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
        return [self._prepare_callback(self.update_metadata_for_yum_repositories, destination_directory),
                self.get_update_metadata_for_views_callback()]

    def add_package__msi(self, filepath):
        package_name, package_version, platform_string, architecture, extension = parse_filepath(filepath)
        destination_directory = path.join(self.base_directory, 'msi', architecture)
        if not path.exists(destination_directory):
            makedirs(destination_directory)
        logger.info("Copying {!r} to {!r}".format(filepath, destination_directory))
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
        logger.info("Copying {!r} to {!r}".format(filepath, destination_directory))
        copy2(filepath, destination_directory)

    def add_package__ova(self, filepath):
        package_name, package_version, platform_string, architecture, extension = parse_filepath(filepath)
        destination_directory = path.join(self.base_directory, 'ova')
        if not path.exists(destination_directory):
            makedirs(destination_directory)
        logger.info("Copying {!r} to {!r}".format(filepath, destination_directory))
        copy2(filepath, destination_directory)
        return [self._prepare_callback(self.update_metadata_for_views)]

    def add_package__img(self, filepath):
        package_name, package_version, platform_string, architecture, extension = parse_filepath(filepath)
        destination_directory = path.join(self.base_directory, 'img')
        if not path.exists(destination_directory):
            makedirs(destination_directory)
        logger.info("Copying {!r} to {!r}".format(filepath, destination_directory))
        copy2(filepath, destination_directory)
        return [self._prepare_callback(self.update_metadata_for_views)]

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

    def get_hidden_packages(self):
        hidden_filepath = path.join(self.base_directory, 'hidden.json')
        if not path.exists(hidden_filepath):
            return []
        with open(hidden_filepath) as fd:
            return decode(fd.read())

    def set_hidden_packages(self, packages):
        hidden_filepath = path.join(self.base_directory, 'hidden.json')
        with open(hidden_filepath, 'w') as fd:
            return fd.write(encode(list(packages)))

    def gather_metadata_for_views(self):
        all_files = []
        all_files = [filepath for filepath in find_files(self.base_directory, '*')
                     if not self._exclude_filepath_from_views(filepath)
                     and parse_filepath(filepath) != (None, None, None, None, None)]
        distributions = [parse_filepath(distribution) + (distribution, ) for distribution in all_files]
        package_names = set([distribution[0] for distribution in distributions])
        hidden_package_names = self.get_hidden_packages()
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
                       hidden=package_name in hidden_package_names,
                       display_name=' '.join([item.capitalize() for item in package_name.split('-')]),
                       releases=[dict(version=key, distributions=value)
                                 for key, value in sorted(distributions_by_version.items(),
                                                          key=lambda item: parse_version(item[0]),
                                                          reverse=True)])

    def update_metadata_for_yum_repositories(self, yum_repo_dir=None):
        all_yum_repos = glob(path.join(self.base_directory, 'rpm', '*', '*', '*'))
        for dirpath in [yum_repo_dir] if yum_repo_dir else all_yum_repos:
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

    def get_update_metadata_for_views_callback(self):
        return self._prepare_callback(self.update_metadata_for_views)

    def call_callbacks(self, callbacks):
        for item in callbacks:
            item()

    def _write_packages_gz_file(self, dirpath, ftp_base):
        import gzip
        # cache = path.join(self.incoming_directory, "apt_cache.db")
        # pid = log_execute_assert_success(['apt-ftparchive', '--db', cache, 'packages', dirpath])
        pid = log_execute_assert_success(['dpkg-scanpackages', "--multiversion", dirpath, '/dev/null'])
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

    def update_metadata_for_apt_repositories(self, apt_repo_dir=None):
        all_apt_repos = glob(path.join(self.base_directory, 'deb', '*', 'dists', '*', 'main', 'binary-*'))
        for dirpath in [apt_repo_dir] if apt_repo_dir else all_apt_repos:
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
