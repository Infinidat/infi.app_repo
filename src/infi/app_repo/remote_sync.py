# FIXME gevent stuff
from infi.pyutils.lazy import cached_method
from infi.pyutils.contexts import contextmanager


def download_metadata(remote):
    from urllib2 import urlopen
    from cjson import decode
    url = "ftp://{0}/metadata.json".format(remote)
    return decode(urlopen(url).read())


class Analyser(object):
    def __init__(self, remote, base_directory):
        super(Analyser, self).__init__()
        self.remote = remote
        self.base_directory = base_directory

    def get_packages_from_metdata(self, metadata):
        return set(self.iter_filepaths_in_metadata(metadata))

    def iter_filepaths_in_metadata(self, metadata):
        for package_dict in metadata['packages']:
            for release_dict in package_dict['releases']:
                for distribution_dict in release_dict['distributions']:
                    yield distribution_dict['filepath']

    def get_our_metadata(self):
        from infi.app_repo import ApplicationRepository
        return ApplicationRepository(self.base_directory).get_views_metadata()

    def get_their_metadata(self):
        return download_metadata(self.remote)

    @cached_method
    def get_our_packages(self):
        return self.get_packages_from_metdata(self.get_our_metadata())

    @cached_method
    def get_their_packages(self):
        return self.get_packages_from_metdata(self.get_their_metadata())

    @contextmanager
    def open_ignorefile(self, write_at_exit=False):
        from infi.gevent_utils.os import path, close, fopen
        filepath = path.join(self.base_directory, "ignore.{0}.json".format(self.remote))
        if not path.exists(filepath) and not write_at_exit:
            yield
            return
        if write_at_exit:
            from infi.gevent_utils.tempfile import mkstemp
            from infi.gevent_utils.shutil import move
            fd, filepath_tmp = mkstemp()
            close(fd)
            with fopen(filepath_tmp, 'w') as fd:
                yield fd
            move(filepath_tmp, filepath)
        else:
            with fopen(filepath) as fd:
                yield fd

    @cached_method
    def get_ignored_packages(self):
        from cjson import decode
        with self.open_ignorefile() as fd:
            if fd is None:
                return dict(pull=[], push=[])
            return decode(fd.read())

    def get_packages_to_ignore_when_pulling(self):
        return set(self.get_ignored_packages()['pull'])

    def get_packages_to_ignore_when_pushing(self):
        return set(self.get_ignored_packages()['push'])

    def set_packages_to_ignore_when_pulling(self, packages):
        from cjson import encode
        _dict = self.get_ignored_packages()
        _dict['pull'] = list(packages)
        with self.open_ignorefile(True) as fd:
            fd.write(encode(_dict))

    def set_packages_to_ignore_when_pushing(self, packages):
        from cjson import encode
        _dict = self.get_ignored_packages()
        _dict['push'] = list(packages)
        with self.open_ignorefile(True) as fd:
            fd.write(encode(_dict))

    def suggest_packages_to_pull(self):
        """:returns: a 2-tuple of (packages available, packages previously ignored)"""
        ignored = self.get_packages_to_ignore_when_pulling()
        available = self.get_their_packages().difference(self.get_our_packages()).difference(ignored)
        return available, ignored

    def suggest_packages_to_push(self):
        ignored = self.get_packages_to_ignore_when_pushing()
        available = self.get_our_packages().difference(self.get_their_packages()).difference(ignored)
        return available, ignored
