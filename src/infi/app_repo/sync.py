# all functions in this module need to be gevent-friendly
# json_rest and requests are not, at the moment, and we don't want to do patch_all
# so we stick with executing curl and wget here :\

from .utils import temporary_directory_context, path, log_execute_assert_success, read_file, decode


def get_local_packages_json(config, index):
    return decode(read_file(path.join(config.packages_directory, index, 'index', 'packages.json')))


def get_remote_packages_json(remote, index):
    url = "http://{}:{}/packages/{}/index/packages.json".format(remote['address'], remote['http_port'], index)
    return decode(log_execute_assert_success(["curl", url]).get_stdout())


def get_local_releases_for_package(config, package):
    return decode(read_file(path.join(config.artifacts_directory, package['releases_uri'].strip(path.sep))))


def get_remote_releases_for_package(remote, package):
    url = "http://{}:{}/{}".format(remote['address'], remote['http_port'], package['releases_uri'])
    return decode(log_execute_assert_success(["curl", url]).get_stdout())


def _list_to_dict(lst, key='name'):
    return {item[key]: item for item in lst}


def _normalize_remote_url(remote, uri):
    return 'http://{}:{}/{}'.format(remote['address'], remote['http_port'], uri)


def _normlize_local_path(config, uri):
    return 'http://127.0.0.1:{}/{}'.format(config.webserver.port, uri)


def _download_file(url):
    log_execute_assert_success(['wget', url]) # i am lazy
    return path.basename(url)


def _upload_file(address, port, username, password, index, filepath):
    from ftplib import FTP
    from infi.gevent_utils.os import path, fopen
    from infi.app_repo.ftpserver import make_ftplib_gevent_friendly
    make_ftplib_gevent_friendly()
    ftp = FTP()
    ftp.connect(address, port)
    ftp.login(username, password)
    ftp.cwd(index)

    with fopen(filepath) as fd:
        ftp.storbinary("STOR %s" % path.basename(filepath), fd)


def get_local_versions_for_package(config, local_index_name, package_name):
    packages = _list_to_dict(get_local_packages_json(config, local_index_name))
    if package_name not in packages:
        return {}
    return _list_to_dict(get_local_releases_for_package(config, packages[package_name]), 'version')


def get_remote_versions_for_package(remote, remote_index, package_name):
    packages = _list_to_dict(get_remote_packages_json(remote, remote_index))
    if package_name not in packages:
        return {}
    return _list_to_dict(get_remote_releases_for_package(remote, packages[package_name]), 'version')


def get_files_from_versions(versions, specific_platform=None, specific_arch=None):
    files = set()
    for item in versions:
        for distribution in item['distributions']:
            if specific_platform in (distribution['platform'], None):
                if specific_arch in (distribution['architecture'], None):
                    files.add(distribution['filepath'])
    return files


def download_and_upload_files(urls, address, port, username, password, index_name):
    for url in urls:
        with temporary_directory_context() as tempdir:
            basename = _download_file(url)
            _upload_file(address, port, username, password, index_name, basename)


def pull_packages(config, local_index_name, remote_server, remote_index_name,
                  package_name, specific_version=None, specific_platform=None, specific_arch=None):
    remote_servers = _list_to_dict(config.to_builtins()['remote_servers'], 'address')
    assert remote_server in remote_servers
    remote = remote_servers[remote_server]

    we_have = get_local_versions_for_package(config, local_index_name, package_name)
    they_have = get_remote_versions_for_package(remote, remote_index_name, package_name)
    those_missing = {key: value for key, value in they_have.iteritems() if key not in we_have}

    if specific_version in ('latest', 'current'):
        specific_version = sorted(they_have.keys(), key=lambda version: parse_version(version))[-1]

    those_needed = [those_missing.get(specific_version, dict(distributions=[]))] if specific_version else \
                    sorted(those_missing.values(), key=lambda item: item['version'])
    urls = [_normalize_remote_url(remote, uri) for
            uri in get_files_from_versions(those_needed, specific_platform, specific_arch)]

    download_and_upload_files(urls, '127.0.0.1', config.ftpserver.port,
                              config.ftpserver.username, config.ftpserver.password, local_index_name)


def push_packages(config, local_index_name, remote_server, remote_index_name,
                  package_name, specific_version=None, specific_platform=None, specific_arch=None):
    from pkg_resources import parse_version
    remote_servers = _list_to_dict(config.to_builtins()['remote_servers'], 'address')
    assert remote_server in remote_servers
    remote = remote_servers[remote_server]

    we_have = get_local_versions_for_package(config, local_index_name, package_name)
    they_have = get_remote_versions_for_package(remote, remote_index_name, package_name)
    those_missing = {key: value for key, value in we_have.iteritems() if key not in they_have}

    if specific_version in ('latest', 'current'):
        specific_version = sorted(we_have.keys(), key=lambda version: parse_version(version))[-1]

    those_needed = [those_missing.get(specific_version, dict(distributions=[]))] if specific_version else \
                        sorted(those_missing.values(), key=lambda item: item['version'])
    urls = [_normlize_local_path(config, uri) for
            uri in get_files_from_versions(those_needed, specific_platform, specific_arch)]

    download_and_upload_files(urls, remote['address'], remote['ftp_port'],
                              remote['username'], remote['password'], remote_index_name)
