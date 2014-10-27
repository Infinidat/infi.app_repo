from .base import Indexer
from infi.gevent_utils.os import path
from infi.app_repo.utils import ensure_directory_exists


class PythonIndexer(Indexer):
    INDEX_TYPE = "python"

    def are_you_interested_in_file(self, filepath, platform, arch, stable):
        return path.basename(filepath).startswith("python-") and filepath.endswith(".tar.gz")

    def initialise(self):
        ensure_directory_exists(self.base_directory)
