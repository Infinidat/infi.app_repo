from .test_case import TestCase
from infi.app_repo.config import Configuration
from infi.app_repo.install import setup_all
from infi.app_repo.mock import patch_all
from infi.app_repo.scripts.extended import get_counters
from infi.app_repo.utils import log_execute_assert_success
from gevent import sleep


class CountersTestCase(TestCase):
    def test_counters_from_web_and_ftp_servers(self):
        with patch_all(), self.temporary_base_directory_context():
            config = self._get_config_for_test()
            setup_all(config)
            with self.web_server_context(config), self.ftp_server_context(config):
                self._get_from_http(config, "/packages/main-stable/index/packages.json")
                self._get_from_ftp(config, "/packages/main-stable/index/packages.json")
            sleep(1)
            counters = get_counters(config)
            self.assertEquals(counters, {"/packages/main-stable/index/packages.json": 2})

    def _get_from_ftp(self, config, uri):
        log_execute_assert_success(["curl", "ftp://127.0.0.1:{}/{}".format(config.ftpserver.port, uri)])

    def _get_from_http(self, config, uri):
        log_execute_assert_success(["curl", "http://127.0.0.1:{}/{}".format(config.webserver.port, uri)])
