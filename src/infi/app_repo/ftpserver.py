from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import _SpawnerBase
from logging import getLogger
from infi.pyutils.lazy import cached_function
from infi.pyutils.decorators import wraps
from infi.gevent_utils.os import path
from infi.gevent_utils.safe_greenlets import safe_spawn
from gevent.event import Event
from gevent.lock import RLock
from gevent import getcurrent


logger = getLogger(__name__)


def suppress_exceptions(func):
    @wraps(func)
    def decorator(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except:
            logger.exception("ftp callback method {} caught an exception".format(func.__name__))
    return decorator


class AppRepoFtpHandler(FTPHandler):
    banner = "app-repo ftp ready."

    @suppress_exceptions
    def on_file_received(self, filepath):
        logger.info("received {}".format(filepath))
        _, index_name, _ = filepath.rsplit(path.sep, 2)
        self.server.rpc_client.process_filepath_by_name(index_name, filepath)

    @suppress_exceptions
    def on_file_sent(self, filepath):
        key = filepath[filepath.index(self.server.config.artifacts_directory):].replace(self.server.config.artifacts_directory, '')
        self.server.counters[key] = self.server.counters.get(key, 0) + 1

    @suppress_exceptions
    def on_disconnect(self):
        logger.info("client disconnected, {} connections are open".format(self.server._map_len()-1))

    @suppress_exceptions
    def on_connect(self):
        logger.info("client connected, {} connections are now open".format(self.server._map_len()+1))


class SafeGreenletFTPServer(_SpawnerBase):
    """A modified version of base FTPServer class which spawns a
    thread every time a new connection is established.
    """
    poll_timeout = 1.0
    _lock = RLock()
    _exit = Event()

    def __init__(self, *args, **kwargs):
        _SpawnerBase.__init__(self, *args, **kwargs)
        self._greenlet_count = 0

    def _increase(self):
        self._greenlet_count += 1

    def _decrease(self, greenlet):
        self._greenlet_count -= 1

    def _start_task(self, target, *args, **kwargs):
        name = kwargs.pop('name', '')
        self._increase()
        greenlet = safe_spawn(target, *kwargs.pop('args', tuple()), **kwargs)
        greenlet.link(self._decrease)
        greenlet.name = name
        greenlet.is_alive = lambda: not greenlet.ready()
        return greenlet

    def _current_task(self):
        return getcurrent()

    def _map_len(self):
        return self._greenlet_count


@cached_function
def make_pyftpdlib_gevent_friendly():
    from pyftpdlib import ioloop, servers, handlers
    from gevent import socket, select
    import asyncore
    ioloop.select = select
    ioloop.IOLoop = ioloop.Select
    servers.IOLoop = ioloop.Select
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

    server = SafeGreenletFTPServer((config.ftpserver.address, config.ftpserver.port), AppRepoFtpHandler)
    server.socket.setblocking(1)
    server.config = config
    server.rpc_client = get_client(config)
    server.counters = PersistentDict(config.ftpserver_counters_filepath)
    server.counters.load()
    server.max_cons = 256
    server.max_cons_per_ip = 5

    return server
