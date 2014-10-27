import gzip
from .base import Indexer
from infi.app_repo.utils import ensure_directory_exists
from infi.gevent_utils.os import path, remove
from infi.app_repo.utils import temporary_directory_context, log_execute_assert_success, hard_link_or_raise_exception
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
RELEASE_FILE_HEADER = "Codename: {}\nArchitectures: amd64 i386\nComponents: main\n"


def write_to_packages_file(dirpath, contents, mode):
    packages_filepath = path.join(dirpath, 'Packages')
    if path.exists(packages_filepath):
        return
    with open(packages_filepath, mode): # TODO gevent-aware
        pass
    fd = gzip.open(packages_filepath + '.gz', 'wb')
    fd.write(content)
    fd.close()


def apt_ftparchive(cmdline_arguments):
    return log_execute_assert_success(['apt-ftparchive'] + cmdline_arguments).get_stdout()


def dpkg_scanpackages(cmdline_arguments):
    return log_execute_assert_success(['dpkg-scanpackages'] + cmdline_arguments).get_stdout()


class AptIndexer(Indexer):
    INDEX_TYPE = 'apt'

    def initialise(self):
        ensure_directory_exists(self.base_directory)
        for item in ('stable', 'unstable'):
            for distribution_name, distribution_dict in KNOWN_DISTRIBUTIONS.items():
                for version, architectures in distribution_dict.items():
                    for arch in architectures:
                        dirpath = self.deduce_dirname(item, distribution_name, version, arch)
                        ensure_directory_exists(dirpath)
                        write_to_packages_file(dirpath, '', 'w')
                    self.generate_release_file_for_specific_distribution_and_version(stable_string, distribution, version)

    def deduce_dirname(self, stableness, distribution_name, codename, arch): # based on how apt likes it
        return path.join(self.base_directory, stableness, distribution_name, 'dists', codename, 'main', 'binary-%s' % arch)

    def are_you_interested_in_file(self, filepath, platform, arch, stable):
        return filepath.endswith('.deb')

    def generate_release_file_for_specific_distribution_and_version(self, stable_string, distribution, codename):
        dirpath = self.path.join(self.base_directory, stable_string, distribution, 'dists', codename)

        def write_release_file():
            cache = path.join(dirpath, 'apt_cache.db')
            contents = apt_ftparchive(['--db', cache, 'release', dirpath])

            release = path.join(dirpath, 'Release')
            with open(release, 'w') as fd:
                fd.write(RELEASE_FILE_HEADER.format(codename, contents)) # TODO gevent-aware

        def delete_old_release_signature_files():
            in_release = path.join(dirpath, 'InRelease')
            release_gpg = path.join(dirpath, 'Release.gpg')
            for filepath in [in_release, release_gpg]:
                if path.exists(filepath):
                    remove(filepath)

        def sign_release_file():
            log_execute_assert_success(['gpg', '--clearsign', '-o', in_release, release])
            log_execute_assert_success(['gpg', '-abs', '-o', release_gpg, release])

        write_release_file()
        delete_old_release_signature_files()
        sign_release_file()

    def consume_file(self, filepath, platform, arch, stable):
        assert arch in TRANSLATE_ARCH
        linux, distribution_name, codename = platform.split('-')
        stable_dir = self.deduce_dirname('stable', distribution_name, codename, arch)
        unstable_dir = self.deduce_dirname('unstable', distribution_name, codename, arch)

        if stable:
            hard_link_or_raise_exception(filepath, stable_dir)
        hard_link_or_raise_exception(filepath, unstable_dir)

        with temporary_directory_context() as dirpath:
            hard_link_or_raise_exception(filepath, dirpath)
            contents = dpkg_scanpackages('--multiversion', dirpath, '/dev/null')
            if stable:
                write_to_packages_file(stable_dir, '\n' + contents.replace('', ''), 'a')
            write_to_packages_file(unstable_dir, '\n' + contents.replace('', ''), 'a')

        if stable:
            self.generate_release_file_for_specific_distribution_and_version('stable', distribution_name, 'codename')
        self.generate_release_file_for_specific_distribution_and_version('unstable', distribution_name, 'codename')
