from shutil import copy, rmtree
from infi.gevent_utils.os import path, fopen, symlink, remove
from infi.gevent_utils.glob import glob
from pkg_resources import resource_filename
from .utils import log_execute_assert_success, sign_rpm_package, sign_deb_package, ensure_directory_exists, find_files
from infi.gevent_utils.safe_greenlets import safe_joinall, safe_spawn_later


GPG_TEMPLATE = """
%_signature gpg
%_gpg_name  app_repo
%__gpg_sign_cmd %{__gpg} \
    gpg --force-v3-sigs --digest-algo=sha1 --batch --no-verbose --no-armor \
    --passphrase-fd 3 --no-secmem-warning -u "%{_gpg_name}" \
    -sbo %{__signature_filename} %{__plaintext_filename}
"""

GPG_FILENAMES = ['gpg.conf', 'pubring.gpg', 'random_seed', 'secring.gpg', 'trustdb.gpg']


def ensure_incoming_and_rejected_directories_exist_for_all_indexers(config):
    for index_name in config.indexes:
        ensure_directory_exists(path.join(config.rejected_directory, index_name))
        ensure_directory_exists(path.join(config.incoming_directory, index_name))


def initialize_all_indexers(config):
    for index_name in config.indexes:
        for indexer in config.get_indexers(index_name):
            indexer.initialise()


def setup_upstart_services(config):
    from .upstart import install
    install()


def _generate_gpg_key_if_does_not_exist(config):
    """:returns: True if the gpg key existed before"""
    gnupg_directory = path.join(path.expanduser("~"), ".gnupg")
    already_generated = all([path.exists(path.join(gnupg_directory, filename)) for filename in GPG_FILENAMES])
    home_key_path = path.join(path.expanduser("~"), 'gpg.key')
    already_generated = already_generated and path.exists(home_key_path)
    if not already_generated:
        rmtree(gnupg_directory, ignore_errors=True)
        log_execute_assert_success(['gpg', '--batch', '--gen-key',
                                    resource_filename(__name__, 'gpg_batch_file')])
        pid = log_execute_assert_success(['gpg', '--export', '--armor'])
        with fopen(path.join(path.expanduser("~"), ".rpmmacros"), 'w') as fd:
            fd.write(GPG_TEMPLATE)
        with fopen(home_key_path, 'w') as fd:
            fd.write(pid.get_stdout())
    data_key_path = path.join(config.artifacts_directory, 'packages', 'gpg.key')
    if not path.exists(data_key_path):
        copy(home_key_path, data_key_path)
    return not already_generated


def _fix_entropy_generator():
    from os import getuid
    rng_tools_script = '/etc/init.d/rng-tools'
    if not path.exists(rng_tools_script) or getuid() != 0:
        return
    log_execute_assert_success([rng_tools_script, 'stop'], True)
    with fopen("/etc/default/rng-tools", 'a') as fd:
        fd.write("HRNGDEVICE=/dev/urandom\n")
    log_execute_assert_success([rng_tools_script, 'start'], True)


def _import_gpg_key_to_rpm_database():
    key = path.join(path.expanduser("~"), 'gpg.key')
    log_execute_assert_success(['rpm', '--import', key])


def _sign_all_existing_deb_and_rpm_packages(config):
    # this is necessary because we replaced the gpg key
    rpms = set()
    debs = set()
    for index_name in config.indexes:
        rpms |= set(find_files(path.join(config.packages_directory, index_name, 'yum'), '*.rpm'))
        debs |= set(find_files(path.join(config.packages_directory, index_name, 'apt'), '*.deb'))
    greenlets = {safe_spawn_later(0, sign_rpm_package, rpm) for rpm in rpms}
    greenlets |= {safe_spawn_later(0, sign_deb_package, deb) for deb in debs}
    safe_joinall(greenlets)


def _override_symlink(src, dst):
    if path.exists(dst):
        assert path.islink(dst)
        remove(dst)
    symlink(src, dst)


def _ensure_legacy_directory_structure_exists(config):
    def _deb():
        _override_symlink(path.join(config.packages_directory, config.web_server.default_index, 'apt', 'linux-ubuntu'),
                          path.join(config.packages_directory, 'deb'))

    def _rpm():
        for item in glob(path.join(config.packages_directory, 'rpm', '*')):
            remove(item)
        for src in glob(path.join(config.packages_directory, config.web_server.default_index, 'yum', 'linux-*')):
            linux, distro, version, arch = path.basename(src).split('-')
            dst = path.join(config.packages_directory, 'rpm', distro, version, arch)
            ensure_directory_exists(path.dirname(dst))
            _override_symlink(src, dst)

    def _ova_updates():
        ensure_directory_exists(path.join(config.packages_directory, 'ova'))
        _override_symlink(path.join(config.packages_directory, config.web_server.default_index, 'vmware-studio-updates'),
                          path.join(config.packages_directory, 'ova', 'updates'))

    _deb()
    _rpm()
    _ova_updates()


def setup_gpg(config):
    ensure_directory_exists(config.packages_directory)
    _fix_entropy_generator()
    if _generate_gpg_key_if_does_not_exist(config):
        _import_gpg_key_to_rpm_database()
        _sign_all_existing_deb_and_rpm_packages(config)


def setup_all(config):
    config.to_disk()
    setup_gpg(config)
    ensure_incoming_and_rejected_directories_exist_for_all_indexers(config)
    initialize_all_indexers(config)
    if config.production_mode:
        setup_upstart_services(config)
    if config.webserver.support_legacy_uris:
        _ensure_legacy_directory_structure_exists(config)

def destroy_all(config):
    log_execute_assert_success(['rm', '-rf', config.base_directory, '/usr/local/var/lib/rpm', '/var/lib/rpm'])
