from .test_case import TestCase, TemporaryBaseDirectoryTestCase
from infi.app_repo.config import Configuration, WebserverConfiguration, RPCServerConfiguration, FtpServerConfiguration
from infi.gevent_utils.os import path


class GettersTestCase(TestCase):
    def test_get_projectroot(self):
        from infi.app_repo import config
        self.assertTrue(config.get_projectroot().endswith("repo"))

    def test_get_base_directory(self):
        from infi.app_repo import config
        self.assertTrue(config.get_base_directory().endswith("repo%sdata" % path.sep))


class ConfigTestCase(TemporaryBaseDirectoryTestCase):
    def setUp(self):
        super(ConfigTestCase, self).setUp()
        self.config = Configuration.from_disk(None)

    def test_to_json(self):
        self.assertIsInstance(self.config.to_json(), str)

    def test_save_and_load(self):
        self.config.to_disk()
        Configuration.from_disk(self.config.filepath)

    def test_revert_to_defaults(self):
        self.config.reset_to_development_defaults()
        self.assertTrue(self.config.development_mode)
        self.assertFalse(self.config.production_mode)
        self.assertEqual((self.config.webserver.address, self.config.webserver.port), ('127.0.0.1', 8000))
        self.assertEqual((self.config.rpcserver.address, self.config.rpcserver.port), ('127.0.0.1', 8001))
        self.assertEqual((self.config.ftpserver.address, self.config.ftpserver.port), ('127.0.0.1', 8002))
        self.config.reset_to_production_defaults()
        self.assertTrue(self.config.production_mode)
        self.assertFalse(self.config.development_mode)
        self.assertEqual((self.config.webserver.address, self.config.webserver.port), ('0.0.0.0', 80))
        self.assertEqual((self.config.rpcserver.address, self.config.rpcserver.port), ('127.0.0.1', 90))
        self.assertEqual((self.config.ftpserver.address, self.config.ftpserver.port), ('0.0.0.0', 21))
        self.config.webserver.address = '8.8.8.8'
        self.config.webserver.port = 6432
        self.config.reset_to_production_defaults()
        self.assertEqual((self.config.webserver.address, self.config.webserver.port), ('0.0.0.0', 80))

    def test_get_default_indexers(self):
        indexers = self.assertIsInstance(self.config.get_indexers("main"), (list, tuple))

    def test_assert_default_config(self):
        for server_key, server_config in zip(['webserver', 'rpcserver', 'ftpserver'],
                                             [WebserverConfiguration, RPCServerConfiguration, FtpServerConfiguration]):
            self.assertEqual(self.config._data[server_key].address, server_config.address.default)
            self.assertEqual(self.config._data[server_key].port, server_config.port.default)
        self.assertEqual(self.config.webserver.default_index, WebserverConfiguration.default_index.default)
        self.assertEqual(self.config.webserver.support_legacy_uris, WebserverConfiguration.support_legacy_uris.default)
        self.assertEqual(self.config.ftpserver.username, FtpServerConfiguration.username.default)
        self.assertEqual(self.config.ftpserver.password, FtpServerConfiguration.password.default)
        self.assertEqual(self.config.ftpserver.masquerade_address, FtpServerConfiguration.masquerade_address.default)
        self.assertEqual(self.config.remote_servers, Configuration.remote_servers.default)
        self.assertEqual(self.config.base_directory, Configuration.base_directory.default)
        self.assertEqual(self.config.logging_level, Configuration.logging_level.default)
        self.assertEqual(self.config.development_mode, Configuration.development_mode.default)
        self.assertEqual(self.config.production_mode, Configuration.production_mode.default)
        self.assertEqual(self.config.indexes, Configuration.indexes.default)
