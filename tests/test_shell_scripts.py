from .test_case import TestCase
from infi.pyutils.contexts import contextmanager
from infi.execute import execute_assert_success, ExecutionError
from infi.app_repo.config import Configuration
from infi.app_repo.mock import patch_all
from infi.app_repo.install import setup_all
from infi.app_repo.utils import write_file, path
from infi.app_repo import sync
from munch import Munch
from gevent import sleep
from logging import getLogger
from uuid import uuid4
from os import path
logger = getLogger(__name__)


class ShellTestCase(TestCase):
    @contextmanager
    def server_context(self):
        with self.temporary_base_directory_context():
            config = Configuration.from_disk(None)
            setup_all(config)
            with self.ftp_server_context(config), self.rpc_server_context(config), self.web_server_context(config):
                sleep(1)
                yield config

    def download_setup_script(self, config, index_name="main-stable"):
        url = "http://localhost:%s/setup/%s" % (config.webserver.port, index_name)
        execute_assert_success(["wget", url, "-O", "setup.sh"])
        return "setup.sh"

    def get_script(self, config, script_name, index_name="main-stable", package=None, version=None):
        url = "http://localhost:%s/%s/%s" % (config.webserver.port, script_name, index_name)
        if package:
            url += "/%s" % package
            if version:
                url += "/%s" % version
        filename = str(uuid4())
        logger.debug(url)
        execute_assert_success(["wget", url, "-O", filename])
        return path.abspath(filename)

    def get_download_script(self, config, index_name="main-stable", package=None, version=None):
        return self.get_script(config, 'download', index_name, package, version)

    def get_install_script(self, config, index_name="main-stable", package=None, version=None):
        return self.get_script(config, 'install', index_name, package, version)

    def log_script(self, filename):
        with open(filename) as fd:
            logger.debug(fd.read())

    def test_setup_script_is_downloadable(self):
        with patch_all(), self.server_context() as config:
            setup_sh = self.download_setup_script(config)
            with open(setup_sh) as fd:
                assert fd.read() != ''

    def test_download_script__no_such_package(self):
        def _assert(download_sh, cmdline):
            with self.assertRaises(ExecutionError) as _context:
                execute_assert_success(cmdline)
            self.assertEquals(_context.exception.result.get_stdout(), '')
            self.assertIn("package not found", _context.exception.result.get_stderr())

        with patch_all(), self.server_context() as config:
            download_sh = self.get_download_script(config)
            _assert(download_sh, ["sh", download_sh, "no-such-package"])
            download_sh = self.get_download_script(config, package='no-such-package')
            _assert(download_sh, ["sh", download_sh])

    def inject_patch_to_script(self, filename, patch_string):
        with open(filename) as fd:
            before = fd.read()
        after = before.replace('parse_commandline $*', 'parse_commandline $*\n%s\n' % patch_string)
        assert after != before
        with open(filename, 'w') as fd:
            fd.write(after)

    def test_download_script__solaris__no_file(self):
        def _assert(download_sh, cmdline):
            with self.assertRaises(ExecutionError) as _context:
                execute_assert_success(cmdline)
            self.assertEquals(_context.exception.result.get_stdout(), '')
            self.assertIn("file not found", _context.exception.result.get_stderr())

        def _patch(download_sh):
            self.inject_patch_to_script(download_sh, '_system() {\n    echo SunOS\n}')
            self.inject_patch_to_script(download_sh, '_processor() {\n    echo sparc\n}')
            self.inject_patch_to_script(download_sh, '_release() {\n    echo 5.11\n}')

        with patch_all(), self.server_context() as config:
            download_sh = self.get_download_script(config)
            self.log_script(download_sh)
            _patch(download_sh)
            _assert(download_sh, ["sh", download_sh, "no-such-package", "1.0"])
            download_sh = self.get_download_script(config, package='no-such-package', version="1.0")
            _patch(download_sh)
            _assert(download_sh, ["sh", download_sh])

    def test_download_script__solaris(self):
        def _assert(download_sh, cmdline):
            pid = execute_assert_success(cmdline)
            self.assertEquals(pid.get_stdout(), "some-package-1.0-solaris-11-sparc.pkg.gz\n")

        def _patch(download_sh):
            self.inject_patch_to_script(download_sh, '_system() {\n    echo SunOS\n}')
            self.inject_patch_to_script(download_sh, '_processor() {\n    echo sparc\n}')
            self.inject_patch_to_script(download_sh, '_release() {\n    echo 5.11\n}')
            self.inject_patch_to_script(download_sh, '_curl() {\n    echo "$1"\n}')
            self.inject_patch_to_script(download_sh, '_gunzip() {\n    echo "gunzip"\n}')

        with patch_all(), self.server_context() as config:
            download_sh = self.get_download_script(config)
            self.log_script(download_sh)
            _patch(download_sh)
            _assert(download_sh, ["sh", download_sh, "some-package", "1.0"])

    def test_install_script__solaris(self):
        def _assert(install_sh, cmdline):
            pid = execute_assert_success(cmdline)
            self.assertEquals(pid.get_stdout(), "gunzip\npkgadd\n")

        def _patch(install_sh):
            self.inject_patch_to_script(install_sh, '_system() {\n    echo SunOS\n}')
            self.inject_patch_to_script(install_sh, '_processor() {\n    echo sparc\n}')
            self.inject_patch_to_script(install_sh, '_release() {\n    echo 5.11\n}')
            self.inject_patch_to_script(install_sh, '_curl() {\n    echo "$1"\n}')
            self.inject_patch_to_script(install_sh, '_gunzip() {\n    echo "gunzip"\n}')
            self.inject_patch_to_script(install_sh, '_pkgadd() {\n    echo "pkgadd"\n}')

        with patch_all(), self.server_context() as config:
            install_sh = self.get_install_script(config)
            _patch(install_sh)
            self.log_script(install_sh)
            _assert(install_sh, ["sh", install_sh, "some-package", "1.0"])

    def test_pkgadd_fails(self):
        def _assert(install_sh, cmdline):
            with self.assertRaises(ExecutionError):
                pid = execute_assert_success(cmdline)

        def _patch(install_sh):
            self.inject_patch_to_script(install_sh, '_system() {\n    echo SunOS\n}')
            self.inject_patch_to_script(install_sh, '_processor() {\n    echo sparc\n}')
            self.inject_patch_to_script(install_sh, '_release() {\n    echo 5.11\n}')
            self.inject_patch_to_script(install_sh, '_curl() {\n    echo "$1"\n}')
            self.inject_patch_to_script(install_sh, '_gunzip() {\n    echo "gunzip"\n}')
            self.inject_patch_to_script(install_sh, '_pkgadd() {\n    exit 1\n}')

        with patch_all(), self.server_context() as config:
            install_sh = self.get_install_script(config)
            _patch(install_sh)
            self.log_script(install_sh)
            _assert(install_sh, ["sh", install_sh, "some-package", "1.0"])

    def test_install_script__aix(self):
        def _assert(install_sh, cmdline):
            pid = execute_assert_success(cmdline)
            self.assertEquals(pid.get_stdout(), "rpm\n")

        def _patch(install_sh):
            self.inject_patch_to_script(install_sh, '_system() {\n    echo AIX\n}')
            self.inject_patch_to_script(install_sh, '_processor() {\n    echo powerpc\n}')
            self.inject_patch_to_script(install_sh, '_release() {\n    echo 1\n}')
            self.inject_patch_to_script(install_sh, '_osversion() {\n    echo 7\n}')
            self.inject_patch_to_script(install_sh, '_curl() {\n    echo "$1"\n}')
            self.inject_patch_to_script(install_sh, '_rpm() {\n    echo "rpm"\n}')

        with patch_all(), self.server_context() as config:
            install_sh = self.get_install_script(config)
            _patch(install_sh)
            self.log_script(install_sh)
            _assert(install_sh, ["sh", install_sh, "some-package", "1.0"])
