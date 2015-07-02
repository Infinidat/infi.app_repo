from __future__ import absolute_import
from infi.pyutils.contexts import contextmanager
from .utils import ensure_directory_exists, path, write_file
from mock import patch, MagicMock


def pdb_side_effect(*args, **kwargs):
    import pdb; pdb.set_trace()


APT_FTPARCHIVE_RETURN_VALUE = 'ok'
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
    _, tempdir, _ = cmdline_arguments
    result = MagicMock()
    contents = ''
    for filepath in glob(path.join(tempdir, '*.deb')):
        contents += DPKG_SCANPACKGES_OUTPUT.lstrip().format(package_name=str(uuid1()), version='1.0', arch='i386',
                                                            file_size=100, md5_sum=1, sha1_sum=1, sha256_sum=1,
                                                            filepath=filepath)
    return contents


def createrepo_side_effect(dirpath):
    assert path.exists(dirpath)
    ensure_directory_exists(path.join(dirpath, 'repodata'))
    write_file(path.join(dirpath, 'repodata', 'repomd.xml'), '')


def createrepo_update_side_effect(dirpath):
    assert path.exists(path.join(dirpath, 'repodata'))


def setup_gpg_side_effect(config, force_resignature=False):
    ensure_directory_exists(config.packages_directory)
    write_file(path.join(config.packages_directory, 'gpg.key'), '')


def apt_ftparchive_side_effect(cmdline_arguments):
    return ''


@contextmanager
def patch_is_really_functions(is_really_deb=True, is_really_rpm=True):
    with patch("infi.app_repo.indexers.apt.is_really_deb", new=lambda filepath: is_really_deb):
        with patch("infi.app_repo.indexers.yum.is_really_rpm", new=lambda filepath: is_really_rpm):
            with patch("infi.app_repo.indexers.wget.is_really_deb", new=lambda filepath: is_really_deb):
                with patch("infi.app_repo.indexers.wget.is_really_rpm", new=lambda filepath: is_really_rpm):
                    yield


@contextmanager
def patch_all():
    with patch("infi.app_repo.indexers.yum.createrepo") as createrepo:
        with patch("infi.app_repo.indexers.yum.createrepo_update") as createrepo_update:
            with patch("infi.app_repo.indexers.apt.apt_ftparchive") as apt_ftparchive:
                with patch("infi.app_repo.indexers.apt.dpkg_scanpackages") as dpkg_scanpackages:
                    with patch("infi.app_repo.install.setup_gpg") as setup_gpg:
                            with patch("infi.app_repo.utils.sign_rpm_package"):
                                with patch("infi.app_repo.utils.sign_deb_package"):
                                    with patch("infi.app_repo.install._import_gpg_key_to_rpm_database"):
                                        with patch("infi.app_repo.indexers.apt.apt_ftparchive") as apt_ftparchive:
                                            with patch("infi.app_repo.indexers.apt.gpg"):
                                                with patch("infi.app_repo.indexers.yum.sign_repomd"):
                                                    with patch_is_really_functions():
                                                        apt_ftparchive.side_effect = apt_ftparchive_side_effect
                                                        createrepo.side_effect = createrepo_side_effect
                                                        createrepo_update.side_effect = createrepo_update_side_effect
                                                        dpkg_scanpackages.side_effect = dpkg_scanpackages_side_effect
                                                        apt_ftparchive.return_value = APT_FTPARCHIVE_RETURN_VALUE
                                                        setup_gpg.side_effect = setup_gpg_side_effect
                                                        yield


@contextmanager
def empty_context():
    yield
