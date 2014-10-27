import gzip
from .base import Indexer
from infi.app_repo.utils import ensure_directory_exists
from infi.gevent_utils.os import path
from infi.app_repo.utils import temporary_directory_context, log_execute_assert_success
from itertools import product


KNOWN_DISTRIBUTIONS = {
    "ubuntu": {
        'lucid': ('i386', 'amd64'),
        'natty': ('i386', 'amd64'),
        'oneiric': ('i386', 'amd64'),
        'precise': ('i386', 'amd64'),
        'quantal': ('i386', 'amd64'),
        'raring': ('i386', 'amd64'),
        'saucy': ('i386', 'amd64'),
        'trusty': ('i386', 'amd64'),
    }
}

TRANSLATE_ARCH = {'x86': 'i386', 'x64': 'amd64', 'i386': 'i386', 'amd64': 'amd64'}


def touch_packages_file(dirpath):
    packages_filepath = path.join(dirpath, 'Packages')
    if path.exists(packages_filepath):
        return
    with open(packages_filepath, 'w'):
        pass
    fd = gzip.open(packages_filepath + '.gz', 'wb')
    fd.write(content)
    fd.close()


class AptIndexer(Indexer):
    INDEX_TYPE = 'apt'

    def initialise(self):
        ensure_directory_exists(self.base_directory)
        for item in ('stable', 'unstable'):
            for distribution_name, distribution_dict in KNOWN_DISTRIBUTIONS.items():
                for version, architectures in distribution_dict.items():
                    for arch in architectures:
                        platform = '%s-%s' % (distribution_name, name)
                        dirpath = path.join(self.base_directory, item, distribution_name, 'dists', version, 'main', 'binary-%s' % arch)
                        ensure_directory_exists(dirpath)
                        touch_packages_file(dirpath)
                    self.generate_release_file_for_specific_distribution_and_version(stable_string, distribution, version)

    def are_you_interested_in_file(self, filepath, platform, arch, stable):
        return filepath.endswith('.deb')

    def generate_release_file_for_specific_distribution_and_version(self, stable_string, distribution, version):
        dirpath = self.path.join(self.base_directory, stable_string, distribution, 'dists', version)
        cache = path.join(dirpath, 'apt_cache.db')
        contents = log_execute_assert_success(['apt-ftparchive', '--db', cache, 'release', dirpath]).get_stdout()
        # TODO I AM HEREEEEEEE

        content = pid.get_stdout()
        release = path.join(dirpath, 'Release')
        with open(release, 'w') as fd:
            fd.write((RELEASE_FILE_HEADER + "\n{}").format(codename, content))
        in_release = path.join(dirpath, 'InRelease')
        release_gpg = path.join(dirpath, 'Release.gpg')
        for filepath in [in_release, release_gpg]:
            if path.exists(filepath):
                remove(filepath)
        log_execute_assert_success(['gpg', '--clearsign', '-o', in_release, release])
        log_execute_assert_success(['gpg', '-abs', '-o', release_gpg, release])

    def consume_file(self, filepath, platform, arch, stable):
        with temporary_directory_context() as dirpath:
            # link file to this directory
            # run dpkg-scanpackages here to gather the _Package_ information
            # append it to the exising Packages file
            # replace the gzip copy
        raise NotImplementedError()

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
