from .test_case import TestCase
from infi.app_repo.indexers import get_indexers
from infi.app_repo.config import Configuration
from infi.app_repo.install import setup_gpg, ensure_incoming_and_rejected_directories_exist_for_all_indexers, destroy_all
from infi.app_repo.mock import patch_all
from infi.app_repo.utils import path
from infi.pyutils.contexts import contextmanager

class IndexersTestCase(TestCase):
    def test_initialize(self):
        with self._setup_context() as config:
            indexers = get_indexers(config, 'main')
            for item in indexers:
                item.initialise()

    @contextmanager
    def _setup_context(self):
        with self.temporary_base_directory_context(), patch_all():
            config = Configuration.from_disk(None)
            ensure_incoming_and_rejected_directories_exist_for_all_indexers(config)
            setup_gpg(config)
            try:
                yield config
            finally:
                destroy_all(config)

    def write_new_package(self, config, extension):
        filepath = path.join(config.incoming_directory, 'main-stable', 'some-package.%s' % extension)
        with open(filepath, 'w') as fd:
            pass
        return filepath

    def test_apt_consume_file(self):
        from infi.app_repo.indexers.apt import AptIndexer
        import gzip
        with self._setup_context() as config:
            indexer = AptIndexer(config, 'main-stable')
            indexer.initialise()
            filepath = self.write_new_package(config, 'deb')
            self.assertTrue(indexer.are_you_interested_in_file(filepath, 'linux-ubuntu-natty', 'i386'))
            indexer.consume_file(filepath, 'linux-ubuntu-natty', 'i386')

            packages_file = path.join(indexer.base_directory, 'linux-ubuntu', 'dists', 'natty', 'main', 'binary-i386', 'Packages')
            with open(packages_file) as fd:
                packages_contents = fd.read()
                self.assertNotEquals(packages_contents, '')
            with gzip.open(packages_file + '.gz', 'rb') as fd:
                self.assertEquals(packages_contents, fd.read())

            release_dirpath = path.join(indexer.base_directory, 'linux-ubuntu', 'dists', 'natty')
            self.assertTrue(path.exists(path.join(release_dirpath, 'Release')))
            self.assertTrue(path.exists(path.join(release_dirpath, 'Release.gpg')))
            self.assertTrue(path.exists(path.join(release_dirpath, 'InRelease')))
