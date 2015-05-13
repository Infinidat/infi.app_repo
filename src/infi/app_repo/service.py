from __future__ import absolute_import

from logging import getLogger
from infi.gevent_utils.os import remove, path
from infi.gevent_utils.glob import glob
from infi.rpc import ServiceWithSynchronized, rpc_call, synchronized
from infi.rpc import AutoTimeoutClient, IPython_Mixin
from infi.app_repo import errors
from infi.app_repo.utils import hard_link_or_raise_exception, path

logger = getLogger(__name__)

SUPPORTED_ARCHIVES = ['.msi', '.rpm', '.deb', '.tar.gz', '.zip', '.ova', '.img', '.iso']
IDLE_TIMEOUT = 5  # seconds


def process_filepath(config, index, filepath, platform, arch):
    indexers = [indexer for indexer in config.get_indexers(index) if
                indexer.are_you_interested_in_file(filepath, platform, arch)]
    if not indexers:
        raise errors.FileNeglectedByIndexers("all indexers are not interested in file {!r}".format(filepath))
    for indexer in indexers:
        try:
            indexer.consume_file(filepath, platform, arch)
        except errors.FileAlreadyExists, error:
            logger.warning("indexer {} says that file {!r} already exists, moving on".format(indexer, error))
            continue


def process_filepath_by_name(config, index, filepath):
    from .filename_parser import parse_filepath
    package_name, package_version, platform_string, architecture, extension = parse_filepath(filepath)
    return process_filepath(config, index, filepath, platform_string, architecture)


class AppRepoService(ServiceWithSynchronized):
    def __init__(self, config):
        super(AppRepoService, self).__init__()
        self.config = config

    @rpc_call
    @synchronized
    def reload_configuration_from_disk(self):
        self.config = self.config.reload_configuration_from_disk()

    @rpc_call
    @synchronized
    def process_filepath(self, index, filepath, platform, arch):
        assert index in self.config.indexes
        self._try_except_finally_on_filepath(process_filepath, index, filepath, platform, arch)

    @rpc_call
    @synchronized
    def process_filepath_by_name(self, index, filepath):
        assert index in self.config.indexes
        return self._try_except_finally_on_filepath(process_filepath_by_name, index, filepath)

    def _try_except_finally_on_filepath(self, func, index, filepath, *args, **kwargs): # TODO rejection needs a test
        try:
            func(self.config, index, filepath, *args, **kwargs)
        except:
            logger.exception("processing source {} failed, moving it to {}".format(filepath, self.config.rejected_directory))
            try:
                hard_link_or_raise_exception(filepath, path.join(self.config.rejected_directory, index))
            except:
                pass
        finally:
            remove(filepath)

    @rpc_call
    @synchronized
    def process_incoming(self, index):
        assert index in self.config.indexes
        for filepath in glob(path.join(self.config.incoming_directory, index, '*')):
            self._try_except_finally_on_filepath(process_filepath_by_name, index, filepath)

    @rpc_call
    @synchronized
    def rebuild_index(self, index, index_type=None):
        assert index in self.config.indexes
        for indexer in self.config.get_indexers(index):
            if index_type is None or index_type == indexer.INDEX_TYPE:
                indexer.rebuild_index()

    @rpc_call
    @synchronized
    def get_artifacts(self, index, index_type=None):
        assert index in self.config.indexes
        all_files = []
        for indexer in self.config.get_indexers(index):
            if index_type is None or index_type == indexer.INDEX_TYPE:
                all_files.extend(list(indexer.iter_files()))
        return all_files

    @rpc_call
    @synchronized
    def delete_artifact(self, filepath):
        if path.exists(filepath):
            remove(filepath)

    @rpc_call
    @synchronized
    def resign_packages(self):
        from .install import sign_all_existing_deb_and_rpm_packages
        sign_all_existing_deb_and_rpm_packages(self.config)

    @rpc_call
    def sign_rpm_package(self, rpm_filepath):
        from .utils import sign_rpm_package
        return sign_rpm_package(rpm_filepath)


class Client(AutoTimeoutClient, IPython_Mixin):
    pass


def get_client(config):
    from infi.rpc import ZeroRPCClientTransport
    client_transport = ZeroRPCClientTransport("tcp://127.0.0.1:{}".format(config.rpcserver.port))
    return Client(client_transport)
