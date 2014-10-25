import os
import unittest
import tempfile
from infi.app_repo import scripts

class ConfigSectionTestCase(unittest.TestCase):
    def test_show(self):
        scripts.app_repo(["config", "show"])

    def test_show__invalid_file(self):
        scripts.app_repo(["config", "show", "--file=/path/does/not/exist"])

    def test_apply__development(self):
        config_fd, config_file = tempfile.mkstemp()
        os.close(config_fd)
        os.remove(config_file)
        scripts.app_repo(["config", "apply", "development-defaults", "--file=%s" % config_file])

    def test_apply__production(self):
        config_fd, config_file = tempfile.mkstemp()
        os.close(config_fd)
        os.remove(config_file)
        scripts.app_repo(["config", "apply", "production-defaults", "--file=%s" % config_file])
