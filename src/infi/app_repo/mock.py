from __future__ import absolute_import
from infi.pyutils.contexts import contextmanager
from mock import patch


@contextmanager
def patch_all():
    with patch("infi.app_repo.indexers.yum.createrepo"):
        with patch("infi.app_repo.indexers.yum.createrepo_update"):
            with patch("infi.app_repo.indexers.apt.apt_ftparchive")as apt_ftparchive:
                apt_ftparchive.get_stdout.return_value = ''
                yield

@contextmanager
def empty_context():
    yield
