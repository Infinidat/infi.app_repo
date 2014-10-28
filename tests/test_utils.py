from .test_case import TestCase
from infi.app_repo.utils import hard_link_or_raise_exception, temporary_directory_context, path, FileAlreadyExists


class HardLinkTestCase(TestCase):
    def test_hard_link_or_raise_exception(self):
        with temporary_directory_context():
            with open('src', 'w'):
                pass
            with self.assertRaises(FileAlreadyExists):
                hard_link_or_raise_exception('src', '.')
            hard_link_or_raise_exception('src', 'dst')
            with self.assertRaises(FileAlreadyExists):
                hard_link_or_raise_exception('src', 'dst')



