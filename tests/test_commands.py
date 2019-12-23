from .test_case import TemporaryBaseDirectoryTestCase
from infi.pyutils.contexts import contextmanager
from infi.app_repo.config import Configuration
from infi.app_repo.mock import patch_all
from infi.app_repo.scripts.extended import delete_packages
from infi.app_repo.install import ensure_incoming_and_rejected_directories_exist_for_all_indexers as ensure_directories_for_indexers
from mock import patch
from mock import MagicMock
import functools


@contextmanager
def patch_all_and_patch_relevant_indexes():
    with patch_all():
        with patch("infi.app_repo.indexers.apt.AptIndexer.rebuild_index") as apt_rebuild_index:
            with patch("infi.app_repo.indexers.wget.PrettyIndexer.rebuild_index") as wget_rebuild_index:
                with patch("infi.app_repo.indexers.yum.YumIndexer.rebuild_index") as yum_rebuild_index:
                    with patch("infi.app_repo.indexers.python.PythonIndexer.rebuild_index") as python_rebuild_index:
                        with patch("infi.app_repo.indexers.vmware_studio_updates.VmwareStudioUpdatesIndexer.rebuild_index") as vmware_rebuild_index:
                            with patch("infi.app_repo.indexers.pypi.PypiIndexer.rebuild_index") as pypi_rebuild_index:
                                patched_methods = {'APT': apt_rebuild_index, 'WGET': wget_rebuild_index, 'YUM': yum_rebuild_index,
                                                   'PYTHON': python_rebuild_index, 'VMWARE': vmware_rebuild_index, 'PYPI': pypi_rebuild_index}
                                yield patched_methods

@contextmanager
def patch_indexers_iter_files():
    with patch("infi.app_repo.indexers.apt.AptIndexer.iter_files") as apt_iter_files:
        with patch("infi.app_repo.indexers.wget.PrettyIndexer.iter_files") as wget_iter_files:
            with patch("infi.app_repo.indexers.yum.YumIndexer.iter_files") as yum_iter_files:
                with patch("infi.app_repo.indexers.python.PythonIndexer.iter_files") as python_iter_files:
                    with patch("infi.app_repo.indexers.vmware_studio_updates.VmwareStudioUpdatesIndexer.iter_files") as vmware_iter_files:
                        with patch("infi.app_repo.indexers.pypi.PypiIndexer.iter_files") as pypi_iter_files:
                            patched_methods = {'APT': apt_iter_files, 'WGET': wget_iter_files, 'YUM': yum_iter_files,
                                               'PYTHON': python_iter_files, 'VMWARE': vmware_iter_files, 'PYPI': pypi_iter_files}
                            # don't really need to mock all the methods, first one should be enough
                            for method in list(patched_methods.values())[:1]:
                                method.return_value = ['TEST_PKG_1.tar.gz']
                            yield patched_methods


class CommandTestCase(TemporaryBaseDirectoryTestCase):

    def setUp(self):
        super(CommandTestCase, self).setUp()
        self.config = self._get_config_for_test()
        self._test_function = functools.partial(delete_packages, self.config, lambda i: 'TEST' in i,
                                                'main-stable', None)

    def test_package_deletion_no_rebuild(self):
        error_message = 'rebuild_index method for indexer {} should not have been called, called {} times'
        with self.temporary_base_directory_context(), self.rpc_server_context(self.config):
            with patch_all_and_patch_relevant_indexes() as mega_patch:
                self._test_function(None, None, no_rebuild=True)
                for indexer, patched_rebuild_method in mega_patch.items():
                    self.assertFalse(patched_rebuild_method.called,
                                     error_message.format(indexer, patched_rebuild_method.call_count))

    def test_package_deletion_no_rebuild_with_dry_run(self):
        error_message = 'rebuild_index method for indexer {} should not have been called, called {} times'
        with self.temporary_base_directory_context(), self.rpc_server_context(self.config):
            with patch_all_and_patch_relevant_indexes() as mega_patch:
                self._test_function(True, None, no_rebuild=None)
                for indexer, patched_rebuild_method in mega_patch.items():
                    self.assertFalse(patched_rebuild_method.called,
                                     error_message.format(indexer, patched_rebuild_method.call_count))

    def test_package_deletion_no_rebuild_when_nothing_to_delete(self):
        error_message = 'rebuild_index method for indexer {} should not have been called, called {} times'
        with self.temporary_base_directory_context(), self.rpc_server_context(self.config):
            with patch_all_and_patch_relevant_indexes() as mega_patch:
                ensure_directories_for_indexers(self.config)
                self._test_function(None, None, no_rebuild=None)
                for indexer, patched_rebuild_method in mega_patch.items():
                    self.assertFalse(patched_rebuild_method.called,
                                     error_message.format(indexer, patched_rebuild_method.call_count))

    def test_package_deletion_with_rebuild(self):
        error_message = 'rebuild_index method for indexer {} should have been called'
        with self.temporary_base_directory_context(), self.rpc_server_context(self.config):
            with patch_all_and_patch_relevant_indexes() as mega_patch:
                with patch_indexers_iter_files():
                    ensure_directories_for_indexers(self.config)
                    self._test_function(None, True, no_rebuild=None)
                    for indexer, patched_rebuild_method in mega_patch.items():
                        self.assertTrue(patched_rebuild_method.called,
                                        error_message.format(indexer))
