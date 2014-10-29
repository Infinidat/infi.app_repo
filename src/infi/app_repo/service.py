from __future__ import absolute_import

from logging import getLogger
from gevent.queue import Queue, Empty
from infi.gevent_utils.safe_greenlets import safe_spawn
from infi.gevent_utils.os import remove, path
from infi.gevent_utils.glob import glob
from infi.rpc import ServiceWithSynchronized, rpc_call, synchronized
from infi.rpc import AutoTimeoutClient, IPython_Mixin, patched_ipython_getargspec_context
from infi.app_repo import errors
from infi.app_repo.utils import hard_link_or_raise_exception, path

logger = getLogger(__name__)

SUPPORTED_ARCHIVES = ['.msi', '.rpm', '.deb', '.tar.gz', '.zip', '.ova', '.img', '.iso']
IDLE_TIMEOUT = 5  # seconds


def process_filepath(config, index, filepath, platform, arch):
    indexers = [indexer for indexer in config.get_indexers(index) if
                indexer.are_you_interested_in_file(filepath, platform, arch)]
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
    def process_filepath(self, index, filepath, platform, arch):
        self._try_except_finally_on_filepath(process_filepath, index, filepath, platform, arch)

    @rpc_call
    @synchronized
    def process_filepath_by_name(self, index, filepath):
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
        for filepath in glob(path.join(self.config.incoming_directory, index, '*')):
            return self._try_except_finally_on_filepath(process_filepath_by_name, index, filepath)

    @rpc_call
    @synchronized
    def rebuild_index(self, index):
        for indexer in self.config.get_indexers(index):
            indexer.rebuild_index()


class Client(AutoTimeoutClient, IPython_Mixin):
    pass


def get_client(config):
    from infi.rpc import ZeroRPCClientTransport
    client_transport = ZeroRPCClientTransport("tcp://127.0.0.1:{}".format(config.rpcserver.port))
    return Client(client_transport)
