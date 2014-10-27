from .test_case import TestCase, TemporaryBaseDirectoryTestCase
from infi.app_repo.config import Configuration
from infi.gevent_utils.os import path


class GettersTestCase(TestCase):
    def test_get_projectroot(self):
        from infi.app_repo import config
        self.assertTrue(config.get_projectroot().endswith("app_repo"))

    def test_get_base_directory(self):
        from infi.app_repo import config
        self.assertTrue(config.get_base_directory().endswith("app_repo%sdata" % path.sep))


class ConfigTestCase(TemporaryBaseDirectoryTestCase):
    def setUp(self):
        super(ConfigTestCase, self).setUp()
        self.config = Configuration.from_disk(None)

    def test_to_json(self):
        self.assertIsInstance(self.config.to_json(), basestring)

    def test_save_and_load(self):
        self.config.to_disk()
        Configuration.from_disk(self.config.filepath)

    def test_revert_to_defaults(self):
        self.config.reset_to_development_defaults()
        self.assertTrue(self.config.development_mode)
        self.assertFalse(self.config.production_mode)
        self.config.reset_to_production_defaults()
        self.assertTrue(self.config.production_mode)
        self.assertFalse(self.config.development_mode)

    def test_get_default_indexers(self):
        indexers = self.assertIsInstance(self.config.get_indexers("main"), (list, tuple))
