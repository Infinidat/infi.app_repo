from .base import Indexer
from infi.app_repo.utils import hard_link_or_raise_exception, ensure_directory_exists, log_execute_assert_success
from infi.gevent_utils.os import path
from infi.gevent_utils.glob import glob
from logging import getLogger
logger = getLogger(__name__)

KNOWN_PLATFORMS = {
    "redhat-5": ("i686", "x86_64"),
    "redhat-6": ("i686", "x86_64"),
    "redhat-7": ("x86_64", ),
    "centos-5": ("i686", "x86_64"),
    "centos-6": ("i686", "x86_64"),
    "centos-7": ("x86_64", ),
}

TRANSLATE_ARCH = {'x86': 'i686', 'x64': 'x86_64', 'i686': 'i686', 'x86_64': 'x86_64'}


class YumIndexer(Indexer):
    INDEX_TYPE = 'yum'

    def initialise(self):
        ensure_directory_exists(self.base_directory)
        for item in ('stable', 'unstable'):
            for platform, architectures in KNOWN_PLATFORMS.items():
                for arch in architectures:
                    ensure_directory_exists(path.join(self.base_directory, item, '%s-%s' % (platform, arch)))
        self.rebuild_index()

    def are_you_interested_in_file(self, filepath, platform, arch):
        return filepath.endswith('.rpm')

    def consume_file(self, filepath, platform, arch):
        assert arch in TRANSLATE_ARCH
        dirpath = path.join(self.base_directory, '%s-%s' % (platform, TRANSLATE_ARCH[arch]))
        hard_link_or_raise_exception(filepath, dirpath)
        self._update_platform_index(platform)

    def update_index(self):
        for dirpath in glob(path.join(self.base_directory, '*', '*')):
            self._update_platform_index(dirpath)

    def rebuild_index(self):
        for dirpath in glob(path.join(self.base_directory, '*', '*')):
            self._delete_repo_metadata(dirpath)
            self._update_platform_index(dirpath)

    def _update_platform_index(self, platform):
        for item in ('stable', 'unstable'):
            dirpath = path.join(self.base_directory, item, platform)
            try:
                createrepo_update(dirpath)
            except:
                logger.exception("Failed to update metadata, will attempt to remove it and create it from scratch")
                self._delete_repo_metadata(dirpath)
                createrepo(dirpath)

    def _delete_repo_metadata(self, dirpath):
        repodata = path.join(dirpath, 'repodata')
        log_execute_assert_success(['rm', '-rf', repodata])

    def _is_repodata_exists(self, dirpath):
        repodata = path.join(dirpath, 'repodata')
        return path.exists(repodata)


def createrepo_update(dirpath):
    log_execute_assert_success(['createrepo', '--update', dirpath])

def createrepo(dirpath):
    log_execute_assert_success(['createrepo', dirpath])
