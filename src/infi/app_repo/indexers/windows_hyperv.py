from .base import Indexer
from infi.gevent_utils.os import path, symlink, remove
from infi.gevent_utils.glob import glob
from infi.app_repo.filename_parser import parse_filepath, FilenameParsingFailed
from infi.app_repo.utils import ensure_directory_exists, hard_link_or_raise_exception, log_execute_assert_success
from infi.app_repo.utils import ensure_directory_exists

ARCH = "x64_vhd"


class WindowsHypervIndexer(Indexer):
    INDEX_TYPE = "vhd"

    def initialise(self):
        ensure_directory_exists(self.base_directory)

    def are_you_interested_in_file(self, filepath, platform, arch):
        return filepath.endswith(".vhd")

    def consume_file(self, filepath, platform, arch):
        hard_link_or_raise_exception(filepath, self.base_directory)

    def iter_files(self):
        return glob(path.join(self.base_directory, '*.vhd'))

    def rebuild_index(self):
        pass

