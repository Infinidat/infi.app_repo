from __future__ import absolute_import
from infi.pyutils.contexts import contextmanager
from mock import patch, MagicMock


def pdb_side_effect(*args, **kwargs):
    import pdb; pdb.set_trace()


DPKG_SCANPACKGES_OUTPUT = """
Package: {package_name}
Source: {package_name}
Version: {version}
Architecture: {arch}
Maintainer: Infinidat
Filename: {filepath}
Size: {file_size}
MD5sum: {md5_sum}
SHA1: {sha1_sum}
SHA256: {sha256_sum}
Section: unknown
Priority: optional
Homepage: http://www.infinidat.com
Description: Some description

"""

def dpkg_scanpackages_side_effect(cmdline_arguments):
    from uuid import uuid1
    from glob import glob
    from os import path
    _, tempdir, _ = cmdline_arguments
    result = MagicMock()
    contents = ''
    for filepath in glob(path.join(tempdir, '*.deb')):
        contents += DPKG_SCANPACKGES_OUTPUT.lstrip().format(package_name=str(uuid1()), version='1.0', arch='i386',
                                                            file_size=100, md5_sum=1, sha1_sum=1, sha256_sum=1,
                                                            filepath=filepath)
    return contents


@contextmanager
def patch_all():
    with patch("infi.app_repo.indexers.yum.createrepo"):
        with patch("infi.app_repo.indexers.yum.createrepo_update"):
            with patch("infi.app_repo.indexers.apt.apt_ftparchive"):
                with patch("infi.app_repo.indexers.apt.dpkg_scanpackages") as dpkg_scanpackages:
                    dpkg_scanpackages.side_effect = dpkg_scanpackages_side_effect
                    yield

@contextmanager
def empty_context():
    yield
