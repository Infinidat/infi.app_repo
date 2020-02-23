from .test_case import TestCase
from infi.app_repo.indexers import get_indexers
from infi.app_repo.config import Configuration
from infi.app_repo.install import setup_gpg, ensure_incoming_and_rejected_directories_exist_for_all_indexers, destroy_all
from infi.app_repo.mock import patch_all
from infi.app_repo.utils import path, fopen, decode
from infi.pyutils.contexts import contextmanager


def read_json_file(filepath):
    with fopen(filepath) as fd:
        return decode(fd.read())


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
            self.assertTrue(indexer.are_you_interested_in_file(filepath, 'linux-ubuntu-xenial', 'x86'))
            self.assertFalse(indexer.are_you_interested_in_file('foo.rpm', 'linux-ubuntu-xenial', 'x86'))
            indexer.consume_file(filepath, 'linux-ubuntu-xenial', 'i386')

            packages_file = path.join(indexer.base_directory, 'linux-ubuntu', 'dists', 'xenial', 'main', 'binary-i386', 'Packages')
            with fopen(packages_file) as fd:
                packages_contents = fd.read()
                self.assertNotEqual(packages_contents, '')
                self.assertIn("Filename: dists/xenial/main/binary-i386/some-package.deb", packages_contents)
            with gzip.open(packages_file + '.gz', 'rb') as fd:
                self.assertEqual(packages_contents, fd.read().decode())

            release_dirpath = path.join(indexer.base_directory, 'linux-ubuntu', 'dists', 'xenial')
            self.assertTrue(path.exists(path.join(release_dirpath, 'main', 'binary-i386', 'some-package.deb')))

            release_filepath = path.join(release_dirpath, 'Release')
            # with fopen(release_filepath) as fd:
            #     self.assertEquals(fd.read(), 'Codename: xenial\nArchitectures: amd64 i386\nComponents: main\nok')
            self.assertTrue(path.exists(release_filepath))
            # self.assertTrue(path.exists(release_filepath + '.gpg'))
            # self.assertTrue(path.exists(path.join(release_dirpath, 'InRelease')))

    def test_yum_consume_file(self):
        from infi.app_repo.indexers.yum import YumIndexer
        with self._setup_context() as config:
            indexer = YumIndexer(config, 'main-stable')
            indexer.initialise()
            filepath = self.write_new_package_in_incoming_directory(config, extension='rpm')
            self.assertTrue(indexer.are_you_interested_in_file(filepath, 'linux-redhat-7', 'x64'))
            self.assertFalse(indexer.are_you_interested_in_file('foo.deb', 'linux-redhat-7', 'x64'))
            indexer.consume_file(filepath, 'linux-redhat-7', 'x64')

    def test_wget_consume_file(self):
        from infi.app_repo.indexers.wget import PrettyIndexer
        with self._setup_context() as config:
            indexer = PrettyIndexer(config, 'main-stable')
            indexer.initialise()
            filepath = self.write_new_package_in_incoming_directory(config, package_basename='my-app-0.1-linux-ubuntu-xenial-x64', extension='deb')
            self.assertTrue(indexer.are_you_interested_in_file(filepath, 'linux-ubuntu-xenial', 'x64'))
            indexer.consume_file(filepath, 'linux-ubuntu-xenial', 'x64')

            self.assertTrue(path.exists(path.join(indexer.base_directory, 'packages', 'my-app', 'releases', '0.1', 'distributions',
                                                  'linux-ubuntu-xenial', 'architectures', 'x64', 'extensions', 'deb',
                                                  'my-app-0.1-linux-ubuntu-xenial-x64.deb')))
            packages = read_json_file(path.join(indexer.base_directory, 'packages.json'))
            self.assertIsInstance(packages, list)
            self.assertGreater(len(packages), 0)
            releases = read_json_file(path.join(indexer.base_directory, 'packages', 'my-app', 'releases.json'))
            self.assertIsInstance(packages, list)
            self.assertGreater(len(packages), 0)

    def test_wget_consumes_ova(self):
        from infi.app_repo.indexers.wget import PrettyIndexer
        with self._setup_context() as config:
            indexer = PrettyIndexer(config, 'main-stable')
            indexer.initialise()
            filepath = self.write_new_package_in_incoming_directory(config, package_basename='application-repository-0.2.31-linux-ubuntu-lucid-x86_OVF10', extension='ova')
            self.assertTrue(indexer.are_you_interested_in_file(filepath, 'linux-ubuntu-lucid', 'x86_OVF10'))
            indexer.consume_file(filepath, 'linux-ubuntu-lucid', 'x86_OVF10')

            self.assertTrue(path.exists(path.join(indexer.base_directory, 'packages', 'application-repository', 'releases', '0.2.31', 'distributions',
                                                  'vmware-esx', 'architectures', 'x86_OVF10', 'extensions', 'ova',
                                                  'application-repository-0.2.31-linux-ubuntu-lucid-x86_OVF10.ova')))
            packages = read_json_file(path.join(indexer.base_directory, 'packages.json'))
            self.assertIsInstance(packages, list)
            self.assertGreater(len(packages), 0)
            releases = read_json_file(path.join(indexer.base_directory, 'packages', 'application-repository', 'releases.json'))
            self.assertIsInstance(packages, list)
            self.assertGreater(len(packages), 0)

    def test_python_consume_file(self):
        from infi.app_repo.indexers.python import PythonIndexer
        with self._setup_context() as config:
            indexer = PythonIndexer(config, 'main-stable')
            indexer.initialise()
            filepath = self.write_new_package_in_incoming_directory(config, package_basename='python-v2.7.8.13-linux-oracle-7-x64', extension='tar.gz')
            self.assertTrue(indexer.are_you_interested_in_file(filepath, 'linux-oracle-7', 'x64'))
            indexer.consume_file(filepath, 'linux-oracle-7', 'x64')
            print(filepath)
            self.assertTrue(path.exists(path.join(indexer.base_directory, 'python-v2.7.8.13-linux-oracle-7-x64.tar.gz')))
