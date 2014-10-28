from .base import Indexer
from infi.app_repo.utils import hard_link_or_raise_exception, ensure_directory_exists, log_execute_assert_success
from infi.gevent_utils.os import path
from infi.gevent_utils.glob import glob
from logging import getLogger
logger = getLogger(__name__)

KNOWN_PLATFORMS = {
    "linux-redhat-5": ("i686", "x86_64"),
    "linux-redhat-6": ("i686", "x86_64"),
    "linux-redhat-7": ("x86_64", ),
    "linux-centos-5": ("i686", "x86_64"),
    "linux-centos-6": ("i686", "x86_64"),
    "linux-centos-7": ("x86_64", ),
}

TRANSLATE_ARCH = {'x86': 'i686', 'x64': 'x86_64', 'i686': 'i686', 'x86_64': 'x86_64'}


class YumIndexer(Indexer):
    INDEX_TYPE = 'yum'

    def initialise(self):
        ensure_directory_exists(self.base_directory)
        for platform, architectures in KNOWN_PLATFORMS.items():
            for arch in architectures:
                ensure_directory_exists(path.join(self.base_directory, '%s-%s' % (platform, arch)))
        self.rebuild_index()

    def are_you_interested_in_file(self, filepath, platform, arch):
        return filepath.endswith('.rpm') and \
               platform in KNOWN_PLATFORMS and \
               arch in TRANSLATE_ARCH and \
               TRANSLATE_ARCH[arch] in KNOWN_PLATFORMS[platform]

    def consume_file(self, filepath, platform, arch):
        dirpath = path.join(self.base_directory, '%s-%s' % (platform, TRANSLATE_ARCH[arch]))
        hard_link_or_raise_exception(filepath, dirpath)
        self._update_index(platform)

    def update_index(self):
        for dirpath in glob(path.join(self.base_directory, '*')):
            self._update_index(dirpath)

    def rebuild_index(self):
        for dirpath in glob(path.join(self.base_directory, '*')):
            self._delete_repo_metadata(dirpath)
            self._update_index(dirpath)

    def _update_index(self, dirpath):
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
