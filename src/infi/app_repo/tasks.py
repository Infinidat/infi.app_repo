from logging import getLogger
from infi.pyutils.contexts import contextmanager
from . import worker

logger = getLogger(__name__)

@worker.celery.task
def sleep(seconds):
    from time import sleep
    sleep(int(seconds))

@worker.celery.task
def pull_package(remote_fqdn, base_directory, packge_uri):
    from infi.execute import execute_assert_success
    from os import path, makedirs
    from shutil import move
    with temporary_directory_context():
        filename = path.basename(packge_uri)
        if path.exists(filename):
            return
        url = "ftp://{0}/{1}".format(remote_fqdn, packge_uri.strip('/'))
        execute_assert_success(["wget", url])
        dst = path.join(base_directory, "incoming", filename)
        if not path.exists(path.dirname(dst)):
            makedirs(path.dirname(dst))
        move(filename, dst)

@worker.celery.task
def push_package(remote_fqdn, remote_username, remote_password, base_directory, packge_uri):
    from infi.execute import execute_assert_success
    from os import path
    src = path.join(base_directory, packge_uri.strip(path.sep))
    url = "ftp://{0}:{1}@{2}".format(remote_username, remote_password, remote_fqdn)
    execute_assert_success(["curl", "-T", src, url])

@worker.celery.task
def process_incoming(base_directory, force=False):
    from os import path
    from . import ApplicationRepository
    app_repo = ApplicationRepository(base_directory)
    source_path = path.join(base_directory, 'incoming')
    callbacks = app_repo.add(source_path)
    app_repo.call_callbacks([app_repo.update_metadata] if force else callbacks)

@worker.celery.task
def process_source(base_directory, source_path):
    from . import ApplicationRepository
    app_repo = ApplicationRepository(base_directory)
    callbacks = app_repo.add(source_path)
    app_repo.call_callbacks(callbacks)

@worker.celery.task
def update_metadata_for_views(base_directory):
    from os import path
    from . import ApplicationRepository
    app_repo = ApplicationRepository(base_directory)
    app_repo.update_metadata_for_views()

@worker.celery.task
def hide_packages(base_directory, package_names):
    from os import path
    from . import ApplicationRepository
    app_repo = ApplicationRepository(base_directory)
    packages = set(app_repo.get_hidden_packages())
    packages = packages.union(set([package_names] if isinstance(package_names, basestring) else package_names))
    app_repo.set_hidden_packages(packages)
    app_repo.update_metadata_for_views()

def _chdir_and_log(path):
    from os import chdir as _chdir
    _chdir(path)
    logger.debug("Changed directory to {!r}".format(path))

@contextmanager
def chdir(path):
    from os.path import abspath
    from os import curdir
    path = abspath(path)
    current_dir = abspath(curdir)
    _chdir_and_log(path)
    try:
        yield
    finally:
        _chdir_and_log(current_dir)

@contextmanager
def temporary_directory_context():
    from tempfile import mkdtemp
    from shutil import rmtree
    tempdir = mkdtemp()
    with chdir(tempdir):
        yield tempdir
    rmtree(tempdir, ignore_errors=True)
