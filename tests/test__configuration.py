from infi import unittest
from infi.app_repo.config import Configuration

class ConfigurationTestCase(unittest.TestCase):
    def delete_config_file(self):
        from os import remove, path
        if path.exists(Configuration.get_default_config_file()):
            remove(Configuration.get_default_config_file())

    def test__load_save_config(self):
        self.delete_config_file()
        config = Configuration(filepath=Configuration.get_default_config_file())
        config.to_disk()
        Configuration.from_disk(Configuration.get_default_config_file())
