from __future__ import absolute_import

from logging import getLogger
from gevent.queue import Queue, Empty
from infi.gevent_utils.safe_greenlets import safe_spawn
from infi.gevent_utils.os import remove, path
from infi.rpc import ServiceWithSynchronized, rpc_call, synchronized
from infi.rpc import AutoTimeoutClient, IPython_Mixin
from infi.app_repo import ApplicationRepository
from infi.app_repo import errors
from infi.app_repo.utils import hard_link_or_raise_exception

logger = getLogger(__name__)

SUPPORTED_ARCHIVES = ['.msi', '.rpm', '.deb', '.tar.gz', '.zip', '.ova', '.img', '.iso']
IDLE_TIMEOUT = 5  # seconds


class AppRepoService(ServiceWithSynchronized):
    def __init__(self, config, shutdown_callback):
        super(AppRepoService, self).__init__()
        self.config = config
        self.shutdown_callback = shutdown_callback
        self.shutdown = False
        # self.download_queue = Queue()
        # self.download_set = set()
        # self.upload_queue = Queue()
        # self.upload_set = set()
        # self.analyser = Analyser(config.remote.fqdn, config.base_directory)
        # self.app_repo = ApplicationRepository(self.config.base_directory)

    def start(self):
        # self.download_worker = safe_spawn(self.download_worker)
        # self.upload_worker = safe_spawn(self.upload_worker)
        pass

    @rpc_call
    def stop(self):
        logger.info("stop called")
        self.shutdown = True
        # self.download_queue.put(None)
        # self.upload_queue.put(None)
        # self.download_worker.join()
        # self.upload_worker.join()
        self.shutdown_callback()

    def _process_source(self, filepath):
        from os.path import sep
        from .filename_parser import parse_filepath, is_final_version
        from pkg_resources import parse_version

        try:
            package_name, package_version, platform_string, architecture, extension = parse_filepath(filepath)
        except:
            logger.exception("failed parting {}".format(filepath))
            raise errors.FileRejected("filename parsing failed")

        stable = is_final_version(package_version)
        relpath = filepath.replace(self.config.incoming_directory, '').strip(sep)
        index, filename = relpath.split(sep) if sep in relpath else ('main', relpath)
        indexers = [indexer for indexer in self.config.get_indexers(index) if
                    indexer.are_you_interested_in_file(filepath, platform_string, architecture, stable)]
        for indexer in indexers:
            indexer.consume_file(filepath, platform_string, architecture, stable)

    @rpc_call
    @synchronized
    def process_source(self, filepath):
        try:
            self._process_source(filepath)
        except:
            logger.exception("processing source {} failed, moving it to {}".format(filepath, self.config.rejected_directory))
            try:
                hard_link_or_raise_exception(filepath, path.join(self.config.rejected_directory))
            except:
                pass
        finally:
            remove(filepath)

    @rpc_call
    @synchronized
    def process_incoming(self, index):
        raise NotImplementedError()
    # @rpc_call
    # @synchronized
    # def suggest_packages_to_pull(self):
    #     """
    #     :return: (list of locally missing packages, list of ignored packages)
    #     """
    #     return self.analyser.suggest_packages_to_pull()  # return: available, ignored

    # @rpc_call
    # @synchronized
    # def pull_packages(self, packages):
    #     missing_packages, ignored_packages = self.suggest_packages_to_pull()
    #     all_packages = set(missing_packages).union(set(ignored_packages))
    #     packages_to_download = [item for item in packages if item in all_packages]
    #     packages_to_ignore = missing_packages.difference(set(packages_to_download))

    #     self.analyser.set_packages_to_ignore_when_pulling(packages_to_ignore)

    #     # Don't download stuff that's already in the queue.
    #     add_to_queue_packages = set(packages).difference(self.download_set)
    #     self.download_set.update(add_to_queue_packages)
    #     for package in add_to_queue_packages:
    #         self.download_queue.put(package)

    # @rpc_call
    # @synchronized
    # def suggest_packages_to_push(self):
    #     """
    #     :return: (list of remote missing packages, list of ignored packages)
    #     """
    #     return self.analyser.suggest_packages_to_push()  # return: available, ignored

    # @rpc_call
    # @synchronized
    # def push_packages(self, packages):
    #     missing_packages, ignored_packages = self.suggest_packages_to_push()
    #     all_packages = set(missing_packages).union(set(ignored_packages))
    #     packages_to_upload = [item for item in packages if item in all_packages]
    #     packages_to_ignore = missing_packages.difference(set(packages_to_upload))

    #     self.analyser.set_packages_to_ignore_when_pushing(packages_to_ignore)

    #     # Don't upload stuff that's already in the queue.
    #     add_to_queue_packages = set(packages).difference(self.upload_set)
    #     self.upload_set.update(add_to_queue_packages)
    #     for package in add_to_queue_packages:
    #         self.upload_queue.put(package)

    # @rpc_call
    # def upload_package(self, package_uri):
    #     from infi.execute import execute_assert_success
    #     from infi.gevent_utils.os import path
    #     src = path.join(self.config.base_directory, package_uri.strip(path.sep))
    #     url = "ftp://{0}:{1}@{2}".format(self.config.remote.username, self.config.remote.password,
    #                                      self.config.remote.fqdn)
    #     execute_assert_success(["curl", "-T", src, url])

    # @rpc_call
    # def download_package(self, package_uri):
    #     from infi.execute import execute_assert_success
    #     from infi.gevent_utils.os import makedirs, path
    #     from infi.gevent_utils.shutil import move
    #     with temporary_directory_context():
    #         filename = path.basename(package_uri)
    #         if path.exists(filename):
    #             return
    #         url = "ftp://{0}/{1}".format(self.config.remote.fqdn, package_uri.strip('/'))
    #         execute_assert_success(["wget", url])
    #         dst = path.join(self.config.base_directory, "incoming", filename)
    #         if not path.exists(path.dirname(dst)):
    #             makedirs(path.dirname(dst))
    #         move(filename, dst)


    # @rpc_call
    # @synchronized
    # def update_metadata_for_views(self):
    #     self.app_repo.update_metadata_for_views()

    # @rpc_call
    # @synchronized
    # def hide_packages(self, package_names):
    #     packages = set(self.app_repo.get_hidden_packages())
    #     packages = packages.union(set([package_names] if isinstance(package_names, basestring) else package_names))
    #     self.app_repo.set_hidden_packages(packages)
    #     self.app_repo.update_metadata_for_views()

    # @rpc_call
    # @synchronized
    # def get_metadata(self):
    #     return self.app_repo.get_views_metadata()

    # def get_queued_download_items(self):
    #     return list(self.download_set)

    # def get_queued_upload_items(self):
    #     return list(self.upload_set)

    # def download_worker(self):
    #     logger.debug("download worker started.")
    #     while True:
    #         try:
    #             package = self.download_queue.get(timeout=IDLE_TIMEOUT)
    #             if self.shutdown:
    #                 logger.debug("download worker exitting.")
    #                 break
    #             # FIXME error handling on download
    #             logger.debug("download worker started processing package {}".format(package))
    #             self.download_package(package)
    #             logger.debug("download worker finished processing package {}".format(package))
    #             self.download_set.discard(package)
    #         except Empty:
    #             self._process_incoming()

    # def upload_worker(self):
    #     logger.debug("upload worker started.")
    #     while True:
    #         package = self.upload_queue.get()
    #         if self.shutdown:
    #             logger.debug("upload worker exitting.")
    #             break
    #         # FIXME error handling on upload
    #         logger.debug("upload worker started processing package {}".format(package))
    #         self.upload_package(package)
    #         logger.debug("upload worker finished processing package {}".format(package))
    #         self.upload_set.discard(package)


class Client(AutoTimeoutClient, IPython_Mixin):
    pass


def get_client(config):
    from infi.rpc import ZeroRPCClientTransport
    client_transport = ZeroRPCClientTransport("tcp://127.0.0.1:{}".format(config.rpcserver.port))
    return Client(client_transport)
