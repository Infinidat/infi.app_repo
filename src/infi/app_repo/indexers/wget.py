from .base import Indexer
from infi.gevent_utils.os import path
from infi.app_repo.utils import ensure_directory_exists
from infi.gevent_utils.json_utils import encode, decode


def _ensure_packages_json_file_exists_in_directory(dirpath):
    filepath = path.join(dirpath, 'packages.json')
    if path.exists(filepath):
        try:
            with open(filepath) as fd:
                if isinstance(encode(fd.read()), list):
                    return
        except:
            pass
    with open(filepath, 'w') as fd:
        fd.write(encode([], indent=4))


class PrettyIndexer(Indexer): # TODO implement this
    INDEX_TYPE = 'wget'

    def initialise(self):
        dirpath = path.join(self.base_directory)
        ensure_directory_exists(dirpath)
        _ensure_packages_json_file_exists_in_directory(dirpath)

    def are_you_interested_in_file(self, filepath, platform, arch):
        return False

