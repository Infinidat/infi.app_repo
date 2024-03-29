from .base import Indexer
from infi.app_repo.utils import ensure_directory_exists
from infi.gevent_utils.os import path, remove, fopen
from infi.gevent_utils.glob import glob
from infi.gevent_utils.deferred import create_threadpool_executed_func
from infi.app_repo.utils import temporary_directory_context, log_execute_assert_success, hard_link_or_raise_exception
from infi.app_repo.utils import is_really_deb


KNOWN_DISTRIBUTIONS = {
    'linux-ubuntu': {
        'trusty': ('i386', 'amd64'),
        'xenial': ('i386', 'amd64'),
        'bionic': ('amd64', ),
        'focal': ('amd64', ),
        'jammy': ('amd64', ),
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
    return log_execute_assert_success(['apt-ftparchive'] + cmdline_arguments).get_stdout().decode()


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
        release_gpg = release + '.gpg'
        if path.exists(release) and not force:
            return
        # write release file
        contents = apt_ftparchive(['release', dirpath])
        with fopen(release, 'w') as fd:
            available_archs = sorted(KNOWN_DISTRIBUTIONS[distribution][codename])
            fd.write(RELEASE_FILE_HEADER.format(codename, " ".join(available_archs), contents))
        # delete old release signature files
        for filepath in [in_release, release_gpg]:
            if path.exists(filepath):
                remove(filepath)
        # sign release file
        if codename == "trusty":
            # trusty doesn't support SHA256 for InRelease
            gpg(['--clearsign', '--digest-algo', 'SHA1', '-o', in_release, release])
        else:
            gpg(['--clearsign', '--digest-algo', 'SHA256', '-o', in_release, release])
        gpg(['-abs', '-o', release_gpg, release])

    def consume_file(self, filepath, platform, arch):
        from infi.app_repo.utils import sign_deb_package
        distribution_name, codename = platform.rsplit('-', 1)
        dirpath = self.deduce_dirname(distribution_name, codename, arch)
        hard_link_or_raise_exception(filepath, dirpath)
        sign_deb_package(filepath)
        with temporary_directory_context() as tempdir:
            hard_link_or_raise_exception(filepath, tempdir)
            contents = apt_ftparchive(['packages', tempdir])
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
        cache_file = path.join(self.base_directory, 'apt_cache.db')
        for distribution_name, distribution_dict in KNOWN_DISTRIBUTIONS.items():
            for version, architectures in distribution_dict.items():
                for arch in architectures:
                    dirpath = self.deduce_dirname(distribution_name, version, arch)
                    contents = apt_ftparchive(['packages', '--db', cache_file, dirpath])
                    relapath = dirpath.replace(path.join(self.base_directory, distribution_name), '').strip(path.sep)
                    fixed_contents = contents.replace(dirpath, relapath)
                    write_to_packages_file(dirpath, fixed_contents, 'w')
                self.generate_release_file_for_specific_distribution_and_version(distribution_name, version)
