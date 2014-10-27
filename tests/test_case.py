from infi import unittest
from infi.pyutils.contexts import contextmanager
from infi.execute import execute_assert_success
from mock import patch


from time import sleep
from waiting import wait


class TestCase(unittest.TestCase):
    pass


class TemporaryBaseDirectoryTestCase(TestCase):
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

    def setUp(self):
        active_temporary_base_directory_context = self.temporary_base_directory_context()
        active_temporary_base_directory_context.__enter__()
        self.addCleanup(active_temporary_base_directory_context.__exit__, None, None, None)
