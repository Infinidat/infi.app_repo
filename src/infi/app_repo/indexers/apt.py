from .base import Indexer
from infi.app_repo.utils import ensure_directory_exists
from infi.gevent_utils.os import path, remove, fopen
from infi.gevent_utils.glob import glob
from infi.gevent_utils.deferred import create_threadpool_executed_func
from infi.app_repo.utils import temporary_directory_context, log_execute_assert_success, hard_link_or_raise_exception
from infi.app_repo.utils import is_really_deb


KNOWN_DISTRIBUTIONS = {
    'linux-ubuntu': {
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
RELEASE_FILE_HEADER = "Codename: {}\nArchitectures: {}\nComponents: main\n{}"


def write_to_packages_file(dirpath, contents, mode):
    import gzip
    packages_filepath = path.join(dirpath, 'Packages')
    with fopen(packages_filepath, mode) as fd:
        fd.write(contents)
    with fopen(packages_filepath, 'rb') as fd:
        all_contents = fd.read()
    fd = gzip.open(packages_filepath + '.gz', 'wb')
    fd.write(all_contents)
    fd.close()


def apt_ftparchive(cmdline_arguments):
    return log_execute_assert_success(['apt-ftparchive'] + cmdline_arguments).get_stdout()


def dpkg_scanpackages(cmdline_arguments):
    return log_execute_assert_success(['dpkg-scanpackages'] + cmdline_arguments).get_stdout()


def gpg(cmdline_arguments):
    return log_execute_assert_success(['gpg'] + cmdline_arguments).get_stdout()


class AptIndexer(Indexer):
    INDEX_TYPE = 'apt'

    def initialise(self):
        ensure_directory_exists(self.base_directory)
        for distribution_name, distribution_dict in KNOWN_DISTRIBUTIONS.items():
            for version, architectures in distribution_dict.items():
                for arch in architectures:
                    dirpath = self.deduce_dirname(distribution_name, version, arch)
                    ensure_directory_exists(dirpath)
                    if not path.exists(path.join(dirpath, 'Packages')):
                        write_to_packages_file(dirpath, '', 'w')
                self.generate_release_file_for_specific_distribution_and_version(distribution_name, version, False)

    def deduce_dirname(self, distribution_name, codename, arch): # based on how apt likes it
        return path.join(self.base_directory, distribution_name, 'dists', codename, 'main', 'binary-%s' % TRANSLATE_ARCH[arch])

    def are_you_interested_in_file(self, filepath, platform, arch):
        if not filepath.endswith('deb'):
            return False
        if not is_really_deb(filepath):
            return False
        distribution_name, codename = platform.rsplit('-', 1)
        return distribution_name in KNOWN_DISTRIBUTIONS and \
               codename in KNOWN_DISTRIBUTIONS[distribution_name] and \
               arch in TRANSLATE_ARCH and \
               TRANSLATE_ARCH[arch] in KNOWN_DISTRIBUTIONS[distribution_name][codename] and \
               is_really_deb(filepath)

    def generate_release_file_for_specific_distribution_and_version(self, distribution, codename, force=True):
        dirpath = path.join(self.base_directory, distribution, 'dists', codename)
        in_release = path.join(dirpath, 'InRelease')
        release = path.join(dirpath, 'Release')

        def write_release_file():
            cache = path.join(dirpath, 'apt_cache.db')
            contents = apt_ftparchive(['--db', cache, 'release', dirpath])

            def _write():
                with fopen(release, 'w') as fd:
                    available_archs = sorted(KNOWN_DISTRIBUTIONS[distribution][codename])
                    fd.write(RELEASE_FILE_HEADER.format(codename, " ".join(available_archs), contents))

            _write()

        def delete_old_release_signature_files():
            for filepath in [in_release, '%s.gpg' % release]:
                if path.exists(filepath):
                    remove(filepath)

        def sign_release_file():
            gpg(['--clearsign', '-o', in_release, release])
            gpg(['-abs', '-o', '%s.gpg' % release, release])

        if force or not path.exists(release):
            write_release_file()
            delete_old_release_signature_files()
            sign_release_file()

    def consume_file(self, filepath, platform, arch):
        from infi.app_repo.utils import sign_deb_package
        distribution_name, codename = platform.rsplit('-', 1)
        dirpath = self.deduce_dirname(distribution_name, codename, arch)
        hard_link_or_raise_exception(filepath, dirpath)
        sign_deb_package(filepath)
        with temporary_directory_context() as tempdir:
            hard_link_or_raise_exception(filepath, tempdir)
            contents = dpkg_scanpackages(['--multiversion', tempdir, '/dev/null'])
            relapath = dirpath.replace(path.join(self.base_directory, distribution_name), '').strip(path.sep)
            fixed_contents = contents.replace(tempdir, relapath)
            write_to_packages_file(dirpath, fixed_contents, 'a')
        self.generate_release_file_for_specific_distribution_and_version(distribution_name, codename)

    def iter_files(self):
        ensure_directory_exists(self.base_directory)
        for distribution_name, distribution_dict in KNOWN_DISTRIBUTIONS.items():
            for version, architectures in distribution_dict.items():
                for arch in architectures:
                    dirpath = self.deduce_dirname(distribution_name, version, arch)
                    for filepath in glob(path.join(dirpath, '*.deb')):
                        yield filepath

    def rebuild_index(self):
        for distribution_name, distribution_dict in KNOWN_DISTRIBUTIONS.items():
            for version, architectures in distribution_dict.items():
                for arch in architectures:
                    dirpath = self.deduce_dirname(distribution_name, version, arch)
                    contents = dpkg_scanpackages(['--multiversion', dirpath, '/dev/null'])
                    relapath = dirpath.replace(path.join(self.base_directory, distribution_name), '').strip(path.sep)
                    fixed_contents = contents.replace(dirpath, relapath)
                    write_to_packages_file(dirpath, fixed_contents, 'w')
                self.generate_release_file_for_specific_distribution_and_version(distribution_name, version)
