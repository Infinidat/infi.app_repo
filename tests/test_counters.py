from .test_case import TestCase
from infi.app_repo.config import Configuration
from infi.app_repo.install import setup_all
from infi.app_repo.mock import patch_all
from infi.app_repo.scripts import get_counters
from infi.app_repo.utils import log_execute_assert_success
from gevent import sleep


class CountersTestCase(TestCase):
    def test_counters_from_web_and_ftp_servers(self):
        with patch_all(), self.temporary_base_directory_context():
            self.config = Configuration.from_disk(None)
            setup_all(self.config)
            with self.web_server_context(), self.ftp_server_context():
                self._get_from_ftp("/packages/main-stable/index/packages.json")
                self._get_from_http("/packages/main-stable/index/packages.json")
            sleep(1)
            counters = get_counters(self.config)
            self.assertEquals(counters, {"/packages/main-stable/index/packages.json": 2})

    def _get_from_ftp(self, uri):
        log_execute_assert_success(["curl", "ftp://localhost:{}/{}".format(self.config.ftpserver.port, uri)])

    def _get_from_http(self, uri):
        log_execute_assert_success(["curl", "http://localhost:{}/{}".format(self.config.webserver.port, uri)])
