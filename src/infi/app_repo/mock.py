from __future__ import absolute_import
from infi.pyutils.contexts import contextmanager
from mock import patch


@contextmanager
def patch_all():
    with patch("infi.app_repo.indexers.yum.createrepo"):
        with patch("infi.app_repo.indexers.yum.createrepo_update"):
            yield

@contextmanager
def empty_context():
    yield
