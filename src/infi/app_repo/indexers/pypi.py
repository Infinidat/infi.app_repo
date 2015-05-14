from .base import Indexer
from infi.gevent_utils.os import path
from infi.gevent_utils.glob import glob
from infi.app_repo.utils import ensure_directory_exists, hard_link_or_raise_exception
from infi.app_repo.filename_parser import parse_filepath, FilenameParsingFailed


class PypiIndexer(Indexer):
    INDEX_TYPE = "pypi"

    def initialise(self):
        ensure_directory_exists(self.base_directory)

    def are_you_interested_in_file(self, filepath, platform, arch):
        try:
            package_name, package_version, platform_string, architecture, extension = parse_filepath(filepath)
        except FilenameParsingFailed:
            return False
        return platform_string == 'python' and architecture == 'sdist'

    def consume_file(self, filepath, platform, arch):
        package_name, package_version, platform_string, architecture, extension = parse_filepath(filepath)
        directory = path.join(self.base_directory, package_name)
        ensure_directory_exists(directory)
        filename = '{0}-{1}.tar.gz'.format(package_name, package_version)
        hard_link_or_raise_exception(filepath, path.join(directory, filename))

    def iter_files(self):
        return glob(path.join(self.base_directory, '*', '*.tar.gz'))

    def rebuild_index(self):
        pass
