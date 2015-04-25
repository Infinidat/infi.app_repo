from .base import Indexer
from infi.gevent_utils.os import path
from infi.gevent_utils.glob import glob
from infi.app_repo.filename_parser import parse_filepath, FilenameParsingFailed
from infi.app_repo.utils import ensure_directory_exists, hard_link_or_raise_exception, log_execute_assert_success

ARCH = "UPDATE_ZIP"


class VmwareStudioUpdatesIndexer(Indexer):
    INDEX_TYPE = "vmware-studio-updates"

    def initialise(self):
        ensure_directory_exists(self.base_directory)

    def are_you_interested_in_file(self, filepath, platform, arch):
        try:
            package_name, package_version, platform_string, architecture, extension = parse_filepath(filepath)
        except FilenameParsingFailed:
            return False
        if ARCH in architecture:
            return True
        return False

    def _get_latest_update_file_in_directory(self, dirpath):
        from pkg_resources import parse_version
        latest_update_file, latest_version = None, parse_version('0')
        update_files = [filepath for filepath in glob(path.join(dirpath, '*.zip')) if ARCH in filepath]
        for filepath in update_files:
            package_name, package_version, platform_string, architecture, extension = parse_filepath(filepath)
            package_version = parse_version(package_version)
            if package_version > latest_version:
                latest_version = package_version
                latest_update_file = filepath
        return latest_update_file

    def _extract_update(self, dirpath, filepath):
        log_execute_assert_success(["unzip", "-qq", "-f", filepath, "-d", dirpath])

    def consume_file(self, filepath, platform, arch):
        package_name, package_version, platform_string, architecture, extension = parse_filepath(filepath)
        package_dir = path.join(self.base_directory, package_name)
        ensure_directory_exists(package_dir)
        final_filepath = hard_link_or_raise_exception(filepath, package_dir)
        if self._get_latest_update_file_in_directory(package_dir) == final_filepath:
            self._extract_update(package_dir, final_filepath)

    def rebuild_index(self):
        pass
