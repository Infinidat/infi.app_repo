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

    def test_apt_consume_file(self):
        from infi.app_repo.indexers.apt import AptIndexer
        import gzip
        with self._setup_context() as config:
            indexer = AptIndexer(config, 'main-stable')
            indexer.initialise()
            filepath = self.write_new_package_in_incoming_directory(config, extension='deb')
            self.assertTrue(indexer.are_you_interested_in_file(filepath, 'linux-ubuntu-natty', 'x86'))
            indexer.consume_file(filepath, 'linux-ubuntu-natty', 'i386')

            packages_file = path.join(indexer.base_directory, 'linux-ubuntu', 'dists', 'natty', 'main', 'binary-i386', 'Packages')
            with open(packages_file) as fd:
                packages_contents = fd.read()
                self.assertNotEquals(packages_contents, '')
                self.assertIn("Filename: dists/natty/main/binary-i386/some-package.deb", packages_contents)
            with gzip.open(packages_file + '.gz', 'rb') as fd:
                self.assertEquals(packages_contents, fd.read())

            release_dirpath = path.join(indexer.base_directory, 'linux-ubuntu', 'dists', 'natty')
            self.assertTrue(path.exists(path.join(release_dirpath, 'main', 'binary-i386', 'some-package.deb')))

            release_filepath = path.join(release_dirpath, 'Release')
            with open(release_filepath) as fd:
                self.assertEquals(fd.read(), 'Codename: natty\nArchitectures: amd64 i386\nComponents: main\nok')
            self.assertTrue(path.exists(release_filepath))
            self.assertTrue(path.exists(release_filepath + '.gpg'))
            self.assertTrue(path.exists(path.join(release_dirpath, 'InRelease')))

    def test_yum_consume_file(self):
        from infi.app_repo.indexers.yum import YumIndexer
        with self._setup_context() as config:
            indexer = YumIndexer(config, 'main-stable')
            indexer.initialise()
            filepath = self.write_new_package_in_incoming_directory(config, extension='rpm')
            self.assertTrue(indexer.are_you_interested_in_file(filepath, 'linux-redhat-7', 'x64'))
            indexer.consume_file(filepath, 'linux-redhat-7', 'x64')
