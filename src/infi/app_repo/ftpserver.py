from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer
from logging import getLogger
from infi.pyutils.lazy import cached_function
from infi.gevent_utils.os import path
from gevent import select
logger = getLogger(__name__)


class AppRepoFtpHandler(FTPHandler):
    banner = "app-repo ftp ready."

    def on_file_received(self, filepath):
        logger.info("received {}".format(filepath))
        _, index_name, _ = filepath.rsplit(path.sep, 2)
        self.server.rpc_client.process_filepath_by_name(index_name, filepath)

    def on_file_send(self, filepath): # we implement this for testing purposes
        pass


@cached_function
def make_pyftpdlib_gevent_friendly():
    from pyftpdlib import ioloop
    ioloop.select = select
    ioloop.IOLoop = ioloop.Select


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

    make_pyftpdlib_gevent_friendly()
    disable_ioloop_logging()
    setup_authorization(config)

    server = FTPServer((config.ftpserver.address, config.ftpserver.port), AppRepoFtpHandler)
    server.rpc_client = get_client(config)
    server.max_cons = 256
    server.max_cons_per_ip = 5

    return server
