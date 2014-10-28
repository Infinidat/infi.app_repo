from .test_case import TestCase
from infi.app_repo import service
from infi.app_repo.config import Configuration
from infi.app_repo.indexers.base import Indexer
from infi.app_repo.install import ensure_incoming_and_rejected_directories_exist_for_all_indexers
class DummyIndexer(Indexer):
    def __init__(self, *args, **kwargs):
        super(DummyIndexer, self).__init__(*args, **kwargs)
        self.consumed = False

    def are_you_interested_in_file(self, filepath, platform, arch):
        return True

    def consume_file(self, filepath, platform, arch):
        self.consumed = True


class ServiceTestCase(TestCase):
    def test_process_filepath_by_name(self):
        with self.temporary_base_directory_context():
            config = Configuration.from_disk(None)
            ensure_incoming_and_rejected_directories_exist_for_all_indexers(config)
            filepath = self.write_new_package_in_incoming_directory(config, package_basename='some-package-1.0-linux-redhat-7-x64', extension='rpm')
            indexer = DummyIndexer(config, 'main-stable')
            config.get_indexers = lambda name: [indexer]
            service.process_filepath_by_name(config, filepath)
            self.assertTrue(indexer.consumed)
