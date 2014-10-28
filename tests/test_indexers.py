from .test_case import TestCase
from infi.app_repo.indexers import get_indexers
from infi.app_repo.config import Configuration
from infi.app_repo.install import setup_gpg, ensure_incoming_and_rejected_directories_exist_for_all_indexers
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
            yield config

    def write_new_package(self, config, extension):
        with open(path.join(config.incoming_directory, 'main-stable', 'some-package.%s' % extension), 'w') as fd:
            pass

    def test_apt_consume_file(self):
        from infi.app_repo.indexers.apt import AptIndexer
        with self._setup_context() as config:
            indexer = AptIndexer(config, 'main-stable')
            indexer.initialise()
            self.write_new_package(config, 'deb')
            # TODO I AM HERE

