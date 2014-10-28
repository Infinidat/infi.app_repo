from __future__ import absolute_import
from infi.pyutils.contexts import contextmanager
from mock import patch


def pdb_side_effect(*args, **kwargs):
    import pdb; pdb.set_trace()

@contextmanager
def patch_all():
    with patch("infi.app_repo.indexers.yum.createrepo"):
        with patch("infi.app_repo.indexers.yum.createrepo_update"):
            with patch("infi.app_repo.indexers.apt.apt_ftparchive") as apt_ftparchive:
                with patch("infi.app_repo.indexers.apt.dpkg_scanpackages") as dpkg_scanpackages:
                    dpkg_scanpackages.side_effect = pdb_side_effect
                    yield

@contextmanager
def empty_context():
    yield
