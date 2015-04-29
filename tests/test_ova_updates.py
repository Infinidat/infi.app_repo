import unittest
import mock
from infi.app_repo.indexers import vmware_studio_updates
from infi.app_repo import utils
from infi.gevent_utils.os import path
from munch import Munch

INDEX = 'main-stable'

class TestCase(unittest.TestCase):
    def setUp(self):
        tempdir_context = utils.temporary_directory_context()
        self.tempdir = tempdir_context.__enter__()
        self.config = Munch(packages_directory=self.tempdir)
        self.addCleanup(tempdir_context.__exit__, None, None, None)

    def test_initialise(self):
        indexer = vmware_studio_updates.VmwareStudioUpdatesIndexer(self.config, INDEX)
        self.assertFalse(path.exists(indexer.base_directory))
        indexer.initialise()
        self.assertTrue(path.exists(indexer.base_directory))

    def test_are_you_interested_in_file(self):
        indexer = vmware_studio_updates.VmwareStudioUpdatesIndexer(self.config, INDEX)
        indexer.initialise()
        self.assertTrue(indexer.are_you_interested_in_file("host-power-tools-for-vmware-1.7.4-vmware-esx-x86_OVF10_UPDATE_ZIP.zip", '', ''))

    def test_consume_file(self):
        indexer = vmware_studio_updates.VmwareStudioUpdatesIndexer(self.config, INDEX)
        indexer.initialise()
        src = 'host-power-tools-for-vmware-1.6.13-vmware-esx-x86_OVF10_UPDATE_ZIP.zip'
        dst = path.join(indexer.base_directory, 'host-power-tools-for-vmware')
        utils.write_file(src, '')
        with mock.patch.object(vmware_studio_updates, 'log_execute_assert_success') as log_execute_assert_success:
            indexer.consume_file(src, '', '')
        self.assertTrue(path.exists(path.join(indexer.base_directory, 'host-power-tools-for-vmware', src)))
        log_execute_assert_success.assert_called_with(['unzip', '-qq', '-o', path.join(dst, src), '-d', dst])

        src = 'host-power-tools-for-vmware-1.7.4-vmware-esx-x86_OVF10_UPDATE_ZIP.zip'
        utils.write_file(src, '')
        with mock.patch.object(vmware_studio_updates, 'log_execute_assert_success') as log_execute_assert_success:
            indexer.consume_file(src, '', '')
        log_execute_assert_success.assert_called_with(['unzip', '-qq', '-o', path.join(dst, src), '-d', dst])

        src = 'host-power-tools-for-vmware-1.7.3-vmware-esx-x86_OVF10_UPDATE_ZIP.zip'
        utils.write_file(src, '')
        with mock.patch.object(vmware_studio_updates, 'log_execute_assert_success') as log_execute_assert_success:
            indexer.consume_file(src, '', '')
        log_execute_assert_success.assert_not_called()

        self.assertTrue("1.7.4" in indexer._get_latest_update_file_in_directory(path.join(indexer.base_directory, 'host-power-tools-for-vmware')))
