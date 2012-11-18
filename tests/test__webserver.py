from .test_case import TestCase
from urllib2 import urlopen
from infi.execute import execute_assert_success

class WebserverTestCase(TestCase):
    def test_home(self):
        with self.with_webserver_running():
            content = urlopen("http://localhost:8080").read()
            self.assertIn("Available packages", content)

    def test_pull(self):
        with self.with_new_devlopment_config_file() as configfile:
            cmd = "bin/app_repo -f {} remote set repo.lab.il.infinidat.com beats me".format(configfile)
            execute_assert_success(cmd, shell=True)
            with self.with_webserver_running(configfile):
                content = urlopen("http://localhost:8080/pull").read()
