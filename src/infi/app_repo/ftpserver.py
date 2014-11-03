from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer
from logging import getLogger
from infi.pyutils.lazy import cached_function
from infi.gevent_utils.os import path
logger = getLogger(__name__)


class AppRepoFtpHandler(FTPHandler):
    banner = "app-repo ftp ready."

    def on_file_received(self, filepath):
        logger.info("received {}".format(filepath))
        _, index_name, _ = filepath.rsplit(path.sep, 2)
        self.server.rpc_client.process_filepath_by_name(index_name, filepath)

    def on_file_sent(self, filepath):
        key = filepath[filepath.index(self.server.config.artifacts_directory):].replace(self.server.config.artifacts_directory, '')
        self.server.counters[key] = self.server.counters.get(key, 0) + 1


@cached_function
def make_pyftpdlib_gevent_friendly():
    from pyftpdlib import ioloop, servers, handlers
    from gevent import socket, select
    import asyncore
    ioloop.select = select
    ioloop.IOLoop = ioloop.Select
    ioloop.socket = socket
    servers.socket = socket
    handlers.socket = socket
    asyncore.socket = socket
    asyncore.select = select

@cached_function
def make_ftplib_gevent_friendly():
    import ftplib
    from gevent import socket
    ftplib.socket = socket


@cached_function
def disable_ioloop_logging():
    from pyftpdlib import ioloop
    ioloop._config_logging = lambda *args, **kwargs: None


def setup_authorization(config):
    authorizer = DummyAuthorizer()
    authorizer.add_user(config.ftpserver.username, config.ftpserver.password, config.incoming_directory, perm='lrwe')
    authorizer.add_anonymous(config.artifacts_directory)
    AppRepoFtpHandler.authorizer = authorizer


def start(config):
    from .service import get_client
    from .persistent_dict import PersistentDict
    make_pyftpdlib_gevent_friendly()
    disable_ioloop_logging()
    setup_authorization(config)

    server = FTPServer((config.ftpserver.address, config.ftpserver.port), AppRepoFtpHandler)
    server.socket.setblocking(1)
    server.config = config
    server.rpc_client = get_client(config)
    server.counters = PersistentDict(config.ftpserver_counters_filepath)
    server.counters.load()
    server.max_cons = 256
    server.max_cons_per_ip = 5

    return server
