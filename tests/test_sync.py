from .test_case import TestCase
from infi.pyutils.contexts import contextmanager
from infi.app_repo.config import Configuration, RemoteConfiguration
from infi.app_repo.mock import patch_all
from infi.app_repo.install import setup_all
from infi.app_repo.utils import write_file, path
from infi.app_repo import sync
from munch import Munch
from gevent import sleep


class SyncTestCase(TestCase):
    @contextmanager
    def source_context(self):
        with self.temporary_base_directory_context():
            config = Configuration.from_disk(None)
            setup_all(config)
            with self.ftp_server_context(config), self.rpc_server_context(config), self.web_server_context(config):
                yield config

    @contextmanager
    def target_context(self):
        with self.temporary_base_directory_context():
            config = Configuration.from_disk(None)
            config.ftpserver.port += 10
            config.webserver.port += 10
            config.rpcserver.port += 10
            setup_all(config)
            with self.ftp_server_context(config), self.rpc_server_context(config), self.web_server_context(config):
                yield config

    def upload_dummy_package(self, config):
        filename =  "my-app-0.1-linux-ubuntu-natty-x64.deb"
        write_file(filename, "")
        sync._upload_file('127.0.0.1', config.ftpserver.port, config.ftpserver.username, config.ftpserver.password,
                          'main-stable', filename)
        return filename

    def assert_package_exists(self, config, package_name):
        assert path.exists(path.join(config.packages_directory, 'main-stable', 'index', 'packages', package_name))

    def test_push(self):
        with patch_all():
            with self.source_context() as source:
                self.upload_dummy_package(source)
                sleep(1)
                with self.target_context() as target:
                    source.remote_servers = [RemoteConfiguration(dict(address='127.0.0.1',
                                                                      http_port=target.webserver.port,
                                                                      ftp_port=target.ftpserver.port,
                                                                      username=target.ftpserver.username,
                                                                      password=target.ftpserver.password))]
                    sync.push_packages(source, 'main-stable', '127.0.0.1', 'main-stable', 'my-app')
                    sleep(1)
                    self.assert_package_exists(target, "my-app")

    def test_pull(self):
        with patch_all():
            with self.source_context() as source:
                with self.target_context() as target:
                    self.upload_dummy_package(target)
                    sleep(1)
                    source.remote_servers = [RemoteConfiguration(dict(address='127.0.0.1',
                                                                      http_port=target.webserver.port,
                                                                      ftp_port=target.ftpserver.port))]
                    sync.pull_packages(source, 'main-stable', '127.0.0.1', 'main-stable', 'my-app')
                    sleep(1)
                    self.assert_package_exists(source, "my-app")
