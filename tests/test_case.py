from infi import unittest
from infi.pyutils.contexts import contextmanager
from infi.app_repo.utils import path, fopen
from infi.app_repo.config import Configuration
from mock import patch
from logging import getLogger
from logbook.concurrency import enable_gevent
logger = getLogger(__name__)
enable_gevent()


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
    def ftp_client_context(self, config, login_with_credentials_in_config=False):
        from ftplib import FTP
        from infi.app_repo.ftpserver import make_ftplib_gevent_friendly
        make_ftplib_gevent_friendly()

        client = FTP()
        client.connect('127.0.0.1', self.config.ftpserver.port)
        if login_with_credentials_in_config:
            client.login(config.ftpserver.username, config.ftpserver.password)
        else:
            client.login()
        self.addCleanup(client.close)
        try:
            yield client
        finally:
            client.close()

    @contextmanager
    def ftp_server_context(self, config):
        from gevent import spawn, Timeout
        from infi.app_repo import ftpserver
        server = ftpserver.start(config)
        serving = spawn(server.serve_forever)
        serving.start()
        try:
            yield server
        finally:
            serving.kill(KeyboardInterrupt)
            serving.join()

    @contextmanager
    def patch_is_really_functions(self):
        from infi.app_repo.mock import patch_is_really_functions
        with patch_is_really_functions():
            yield

    @contextmanager
    def rpc_server_context(self, config):
        from infi.rpc import Server, ZeroRPCServerTransport
        from infi.app_repo.service import AppRepoService

        transport = ZeroRPCServerTransport.create_tcp(config.rpcserver.port, config.rpcserver.address)
        service = AppRepoService(config)

        server = Server(transport, service)
        server.bind()

        try:
            with self.patch_is_really_functions():
                yield server
        finally:
            server.request_shutdown()
            server._shutdown_event.wait()
            server.unbind()

    @contextmanager
    def web_server_context(self, config):
        from infi.app_repo.webserver import start
        webserver = start(config)
        try:
            yield
        finally:
            webserver.close()

    def write_new_package_in_incoming_directory(self, config, index='main-stable', package_basename='some-package', extension=None):
        filepath = path.join(config.incoming_directory, index, ('%s.%s' % (package_basename, extension)) if extension else package_basename)
        with fopen(filepath, 'w') as fd:
            pass
        logger.debug("write_new_package_in_incoming_directory %s" % filepath)
        return filepath

    def _get_config_for_test(self):
        """Private method for testing- returns Configuration for testing purposes"""
        config = Configuration.from_disk(None)
        config.reset_to_development_defaults()
        return config


class TemporaryBaseDirectoryTestCase(TestCase):
    def setUp(self):
        active_temporary_base_directory_context = self.temporary_base_directory_context()
        active_temporary_base_directory_context.__enter__()
        self.addCleanup(active_temporary_base_directory_context.__exit__, None, None, None)
