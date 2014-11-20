from .base import Indexer
from infi.gevent_utils.os import path
from infi.app_repo.utils import ensure_directory_exists


class VmwareStudioUpdatesIndexer(Indexer):
    INDEX_TYPE = "vmware-studio-updates"

    def initialise(self):
        ensure_directory_exists(self.base_directory)

    def are_you_interested_in_file(self, filepath, platform, arch):
        return False

    def consume_file(self, filepath, platform, arch):
        raise NotImplementedError()

    def rebuild_index(self):
        pass

