from .base import Indexer
from infi.app_repo.utils import ensure_directory_exists
from infi.gevent_utils.os import path
from itertools import product

KNWON_VERSIONS = ('lucid', 'natty', 'oneiric', 'precise', 'quantal', 'raring', 'saucy', 'trusty')
KNOWN_ARCHS = ("amd64", "i386")


class AptIndexer(Indexer):
    INDEX_TYPE = 'apt'

    def initialise(self):
        ensure_directory_exists(self.base_directory)
        for version, arch in product(KNWON_VERSIONS, KNOWN_ARCHS):
            platform = 'ubuntu-%s' % version
            dirpath = path.join(self.base_directory, 'dists', platform, 'main', 'binary-%s' % arch)
            ensure_directory_exists(dirpath)


# RELEASE_FILE_HEADER = "Codename: {}\nArchitectures: am64 i386\nComponents: main"

#     def _write_release_file(self, dirpath):
#         base, deb, distribution_name, dists, codename = dirpath.rsplit('/', 4)
#         cache = path.join(self.incoming_directory, "apt_cache.db")
#         pid = log_execute_assert_success(['apt-ftparchive', '--db', cache, 'release', dirpath])
#         content = pid.get_stdout()
#         release = path.join(dirpath, 'Release')
#         with open(release, 'w') as fd:
#             fd.write((RELEASE_FILE_HEADER + "\n{}").format(codename, content))
#         in_release = path.join(dirpath, 'InRelease')
#         release_gpg = path.join(dirpath, 'Release.gpg')
#         for filepath in [in_release, release_gpg]:
#             if path.exists(filepath):
#                 remove(filepath)
#         log_execute_assert_success(['gpg', '--clearsign', '-o', in_release, release])
#         log_execute_assert_success(['gpg', '-abs', '-o', release_gpg, release])

#     def update_metadata_for_apt_repositories(self, apt_repo_dir=None):
#         all_apt_repos = glob(path.join(self.base_directory, 'deb', '*', 'dists', '*', 'main', 'binary-*'))
#         for dirpath in [apt_repo_dir] if apt_repo_dir else all_apt_repos:
#             if not path.isdir(dirpath):
#                 continue
#             base, deb, distribution_name, dists, codename, main, binary = dirpath.rsplit('/', 6)
#             ftp_base = path.join(base, deb, distribution_name)
#             self._write_packages_gz_file(dirpath, ftp_base)
#         for dirpath in glob(path.join(self.base_directory, 'deb', '*', 'dists', '*')):
#             if not path.isdir(dirpath):
#                 continue
#             self._write_release_file(dirpath)

#     def _write_packages_gz_file(self, dirpath, ftp_base):
#         import gzip
#         # cache = path.join(self.incoming_directory, "apt_cache.db")
#         # pid = log_execute_assert_success(['apt-ftparchive', '--db', cache, 'packages', dirpath])
#         pid = log_execute_assert_success(['dpkg-scanpackages', "--multiversion", dirpath, '/dev/null'])
#         content = pid.get_stdout()
#         content = content.replace(ftp_base + '/', '')
#         packages = path.join(dirpath, 'Packages')
#         with open(packages, 'w') as fd:
#             fd.write(content)
#         fd = gzip.open(packages + '.gz', 'wb')
#         fd.write(content)
#         fd.close()
