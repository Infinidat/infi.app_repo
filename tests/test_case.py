from infi import unittest
from infi.pyutils.contexts import contextmanager
from infi.app_repo.utils import path
from mock import patch
from logging import getLogger
logger = getLogger(__name__)


class TestCase(unittest.TestCase):
    @contextmanager
    def temporary_base_directory_context(self):
        from infi.app_repo.utils import temporary_directory_context
        with patch("infi.app_repo.config.get_base_directory") as get_base_directory:
            with temporary_directory_context() as tempdir:
                from infi.app_repo.config import Configuration
                get_base_directory.return_value = tempdir
                previous_base_directory = Configuration.base_directory.default
                Configuration.base_directory._default = tempdir
                try:
                    yield tempdir
                finally:
                    Configuration.base_directory._default = previous_base_directory

    @contextmanager
    def ftp_client_context(self, login=False):
        from ftplib import FTP
        from infi.app_repo.ftpserver import make_ftplib_gevent_friendly
        make_ftplib_gevent_friendly()

        client = FTP()
        client.connect('127.0.0.1', self.config.ftpserver.port)
        if login:
            client.login(self.config.ftpserver.username, self.config.ftpserver.password)
        else:
            client.login()
        self.addCleanup(client.close)
        try:
            yield client
        finally:
            client.close()

    @contextmanager
    def ftp_server_context(self):
        from gevent import spawn
        from infi.app_repo import ftpserver
        server = ftpserver.start(self.config)
        serving = spawn(server.serve_forever)
        serving.start()
        try:
            yield server
        finally:
            server.close_all()
            serving.join()

    @contextmanager
    def rpc_server_context(self):
        from infi.rpc import Server, ZeroRPCServerTransport
        from infi.app_repo.service import AppRepoService

        transport = ZeroRPCServerTransport.create_tcp(self.config.rpcserver.port, self.config.rpcserver.address)
        service = AppRepoService(self.config)
        service.start()

        server = Server(transport, service)
        server.bind()

        try:
            yield server
        finally:
            server.request_shutdown()
            server._shutdown_event.wait()
            server.unbind()
            service.stop()

    def write_new_package_in_incoming_directory(self, config, index='main-stable', package_basename='some-package', extension=None):
        filepath = path.join(config.incoming_directory, index, ('%s.%s' % (package_basename, extension)) if extension else package_basename)
        with open(filepath, 'w') as fd:
            pass
        logger.debug("write_new_package_in_incoming_directory %s" % filepath)
        return filepath


class TemporaryBaseDirectoryTestCase(TestCase):
    def setUp(self):
        active_temporary_base_directory_context = self.temporary_base_directory_context()
        active_temporary_base_directory_context.__enter__()
        self.addCleanup(active_temporary_base_directory_context.__exit__, None, None, None)
