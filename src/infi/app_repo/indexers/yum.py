from .base import Indexer
from infi.app_repo.utils import hard_link_or_raise_exception, ensure_directory_exists, log_execute_assert_success
from infi.app_repo.utils import hard_link_and_override, is_really_rpm
from infi.gevent_utils.os import path, remove
from infi.gevent_utils.glob import glob
from logging import getLogger
logger = getLogger(__name__)

CREATEREPO_ARGUMENTS = ['createrepo', '--simple-md-filenames', '--pretty', '--checksum=sha1', '--no-database',
                        '--changelog-limit', '1', '--workers', '10']
KNOWN_PLATFORMS = {
    "linux-redhat-5": ("i686", "x86_64"),
    "linux-redhat-6": ("i686", "x86_64"),
    "linux-redhat-7": ("x86_64", ),
    "linux-centos-5": ("i686", "x86_64"),
    "linux-centos-6": ("i686", "x86_64"),
    "linux-centos-7": ("x86_64", ),
    "linux-suse-10": ("i686", "x86_64"),
    "linux-suse-11": ("i686", "x86_64"),
}

TRANSLATE_ARCH = {'x86': 'i686', 'x64': 'x86_64', 'i686': 'i686', 'x86_64': 'x86_64'}


class YumIndexer(Indexer):
    INDEX_TYPE = 'yum'

    def initialise(self):
        ensure_directory_exists(self.base_directory)
        for platform, architectures in KNOWN_PLATFORMS.items():
            for arch in architectures:
                dirpath = path.join(self.base_directory, '%s-%s' % (platform, arch))
                ensure_directory_exists(path.join(dirpath, 'repodata'))
                gkg_key = path.join(self.config.packages_directory, 'gpg.key')
                hard_link_and_override(gkg_key, path.join(dirpath, 'repodata', 'repomd.xml.key'))
        for dirpath in glob(path.join(self.base_directory, '*')):
            if not self._is_repodata_exists(dirpath):
                createrepo(dirpath)

    def are_you_interested_in_file(self, filepath, platform, arch):
        return filepath.endswith('.rpm') and \
               platform in KNOWN_PLATFORMS and \
               arch in TRANSLATE_ARCH and \
               TRANSLATE_ARCH[arch] in KNOWN_PLATFORMS[platform] and \
               is_really_rpm(filepath)

    def consume_file(self, filepath, platform, arch):
        from infi.app_repo.utils import sign_rpm_package
        dirpath = path.join(self.base_directory, '%s-%s' % (platform, TRANSLATE_ARCH[arch]))
        hard_link_or_raise_exception(filepath, dirpath)
        sign_rpm_package(filepath)
        self._update_index(dirpath)

    def iter_files(self):
        for platform, architectures in KNOWN_PLATFORMS.items():
            for arch in architectures:
                dirpath = path.join(self.base_directory, '%s-%s' % (platform, arch))
                for filepath in glob(path.join(dirpath, '*.rpm')):
                    yield filepath

    def rebuild_index(self):
        for dirpath in glob(path.join(self.base_directory, '*')):
            self._delete_repo_metadata(dirpath)
            self._update_index(dirpath)

    def _update_index(self, dirpath):
        if not self._is_repodata_exists(dirpath):
            createrepo(dirpath)
        else:
            try:
                createrepo_update(dirpath)
            except:
                logger.exception("Failed to update metadata, will attempt to remove it and create it from scratch")
                self._delete_repo_metadata(dirpath)
                createrepo(dirpath)
        sign_repomd(dirpath)

    def _delete_repo_metadata(self, dirpath):
        repodata = path.join(dirpath, 'repodata')
        log_execute_assert_success(['rm', '-rf', repodata])

    def _is_repodata_exists(self, dirpath):
        repodata = path.join(dirpath, 'repodata')
        return path.exists(repodata)


def sign_repomd(dirpath):
    repomd = path.join(dirpath, 'repodata', 'repomd.xml')
    if path.exists('%s.asc'  % repomd):
        remove('%s.asc'  % repomd)
    log_execute_assert_success(['gpg', '-a', '--detach-sign', repomd])



def createrepo_update(dirpath):
    log_execute_assert_success(CREATEREPO_ARGUMENTS + ['--update', '--skip-stat', dirpath])


def createrepo(dirpath):
    log_execute_assert_success(CREATEREPO_ARGUMENTS + [dirpath])
