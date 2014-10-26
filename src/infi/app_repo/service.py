from __future__ import absolute_import

from logbook import Logger
from gevent.queue import Queue, Empty
from infi.gevent_utils.safe_greenlets import safe_spawn
from infi.pyutils.contexts import contextmanager
from infi.rpc import ServiceWithSynchronized, rpc_call, synchronized
from infi.app_repo.analyser import Analyser
from infi.app_repo import ApplicationRepository

logger = Logger(__name__)

SUPPORTED_ARCHIVES = ['.msi', '.rpm', '.deb', '.tar.gz', '.zip', '.ova', '.img', '.iso']


def _chdir_and_log(path):
    from infi.gevent_utils.os import chdir as _chdir
    _chdir(path)
    logger.debug("Changed directory to {!r}".format(path))


@contextmanager
def chdir(path):
    from infi.gevent_utils.os.path import abspath
    from infi.gevent_utils.os import curdir
    path = abspath(path)
    current_dir = abspath(curdir)
    _chdir_and_log(path)
    try:
        yield
    finally:
        _chdir_and_log(current_dir)


@contextmanager
def temporary_directory_context():
    from infi.gevent_utils.tempfile import mkdtemp
    from infi.gevent_utils.os import chdir
    from infi.gevent_utils.shutil import rmtree
    tempdir = mkdtemp()
    try:
        with chdir(tempdir):
            yield tempdir
    finally:
        rmtree(tempdir, ignore_errors=True)


IDLE_TIMEOUT = 5  # seconds


class AppRepoService(ServiceWithSynchronized):
    def __init__(self, config, shutdown_callback):
        super(AppRepoService, self).__init__()
        self.config = config
        self.shutdown_callback = shutdown_callback
        self.download_queue = Queue()
        self.download_set = set()
        self.upload_queue = Queue()
        self.upload_set = set()
        self.analyser = Analyser(config.remote.fqdn, config.base_directory)
        self.app_repo = ApplicationRepository(self.config.base_directory)
        self.shutdown = False

    def start(self):
        self.download_worker = safe_spawn(self.download_worker)
        self.upload_worker = safe_spawn(self.upload_worker)

    @rpc_call
    def stop(self):
        logger.info("stop called")
        self.shutdown = True
        self.download_queue.put(None)
        self.upload_queue.put(None)
        self.download_worker.join()
        self.upload_worker.join()
        self.shutdown_callback()

    @rpc_call
    @synchronized
    def suggest_packages_to_pull(self):
        """
        :return: (list of locally missing packages, list of ignored packages)
        """
        return self.analyser.suggest_packages_to_pull()  # return: available, ignored

    @rpc_call
    @synchronized
    def pull_packages(self, packages):
        missing_packages, ignored_packages = self.suggest_packages_to_pull()
        all_packages = set(missing_packages).union(set(ignored_packages))
        packages_to_download = [item for item in packages if item in all_packages]
        packages_to_ignore = missing_packages.difference(set(packages_to_download))

        self.analyser.set_packages_to_ignore_when_pulling(packages_to_ignore)

        # Don't download stuff that's already in the queue.
        add_to_queue_packages = set(packages).difference(self.download_set)
        self.download_set.update(add_to_queue_packages)
        for package in add_to_queue_packages:
            self.download_queue.put(package)

    @rpc_call
    @synchronized
    def suggest_packages_to_push(self):
        """
        :return: (list of remote missing packages, list of ignored packages)
        """
        return self.analyser.suggest_packages_to_push()  # return: available, ignored

    @rpc_call
    @synchronized
    def push_packages(self, packages):
        missing_packages, ignored_packages = self.suggest_packages_to_push()
        all_packages = set(missing_packages).union(set(ignored_packages))
        packages_to_upload = [item for item in packages if item in all_packages]
        packages_to_ignore = missing_packages.difference(set(packages_to_upload))

        self.analyser.set_packages_to_ignore_when_pushing(packages_to_ignore)

        # Don't upload stuff that's already in the queue.
        add_to_queue_packages = set(packages).difference(self.upload_set)
        self.upload_set.update(add_to_queue_packages)
        for package in add_to_queue_packages:
            self.upload_queue.put(package)

    @rpc_call
    def upload_package(self, package_uri):
        from infi.execute import execute_assert_success
        from infi.gevent_utils.os import path
        src = path.join(self.config.base_directory, package_uri.strip(path.sep))
        url = "ftp://{0}:{1}@{2}".format(self.config.remote.username, self.config.remote.password,
                                         self.config.remote.fqdn)
        execute_assert_success(["curl", "-T", src, url])

    @rpc_call
    def download_package(self, package_uri):
        from infi.execute import execute_assert_success
        from infi.gevent_utils.os import makedirs, path
        from infi.gevent_utils.shutil import move
        with temporary_directory_context():
            filename = path.basename(package_uri)
            if path.exists(filename):
                return
            url = "ftp://{0}/{1}".format(self.config.remote.fqdn, package_uri.strip('/'))
            execute_assert_success(["wget", url])
            dst = path.join(self.config.base_directory, "incoming", filename)
            if not path.exists(path.dirname(dst)):
                makedirs(path.dirname(dst))
            move(filename, dst)

    @rpc_call
    @synchronized
    def process_incoming(self, force=False):
        return self._process_incoming(force)

    def _process_incoming(self, force=False):
        from infi.gevent_utils.os import path
        source_path = path.join(self.config.base_directory, 'incoming')
        from infi.gevent_utils.glob import glob
        found_any_package = False
        for fpath in glob(path.join(source_path, "*")):
            if any(fpath.lower().endswith(e) for e in SUPPORTED_ARCHIVES):
                logger.info("found potential package in incoming directory: {}".format(fpath))
                found_any_package = True
        if found_any_package:
            callbacks = self.app_repo.add(source_path)
            self.app_repo.call_callbacks([self.app_repo.update_metadata] if force else callbacks)

    @rpc_call
    @synchronized
    def process_source(self, source_path):
        callbacks = self.app_repo.add(source_path)
        self.app_repo.call_callbacks(callbacks)

    @rpc_call
    @synchronized
    def update_metadata_for_views(self):
        self.app_repo.update_metadata_for_views()

    @rpc_call
    @synchronized
    def hide_packages(self, package_names):
        packages = set(self.app_repo.get_hidden_packages())
        packages = packages.union(set([package_names] if isinstance(package_names, basestring) else package_names))
        self.app_repo.set_hidden_packages(packages)
        self.app_repo.update_metadata_for_views()

    @rpc_call
    @synchronized
    def get_metadata(self):
        return self.app_repo.get_views_metadata()

    def get_queued_download_items(self):
        return list(self.download_set)

    def get_queued_upload_items(self):
        return list(self.upload_set)

    def download_worker(self):
        logger.debug("download worker started.")
        while True:
            try:
                package = self.download_queue.get(timeout=IDLE_TIMEOUT)
                if self.shutdown:
                    logger.debug("download worker exitting.")
                    break
                # FIXME error handling on download
                logger.debug("download worker started processing package {}".format(package))
                self.download_package(package)
                logger.debug("download worker finished processing package {}".format(package))
                self.download_set.discard(package)
            except Empty:
                self._process_incoming()

    def upload_worker(self):
        logger.debug("upload worker started.")
        while True:
            package = self.upload_queue.get()
            if self.shutdown:
                logger.debug("upload worker exitting.")
                break
            # FIXME error handling on upload
            logger.debug("upload worker started processing package {}".format(package))
            self.upload_package(package)
            logger.debug("upload worker finished processing package {}".format(package))
            self.upload_set.discard(package)


def get_client(config):
    client_transport = ZeroRPCClientTransport("tcp://127.0.0.1:{}".format(config.rpcserver.port))
    return AutoTimeoutClient(client_transport)
