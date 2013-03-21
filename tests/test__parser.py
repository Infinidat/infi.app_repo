from unittest import TestCase
from infi.app_repo import parse_filepath


class ParserTestCase(TestCase):
    def test_host_power_tools(self):
        expected = ('host-power-tools', '0.19.post6.gb4c0e6d', 'linux-redhat-5', 'x86', 'rpm')
        actual = parse_filepath("host-power-tools-0.19.post6.gb4c0e6d-linux-redhat-5-x86.rpm")
        self.assertEquals(actual, expected)

    def test_infinio(self):
        expected = ('infinio-git', '0.9.9.1-6-g41dbd93', 'linux-ubuntu-precise', 'x64', 'deb')
        actual = parse_filepath("infinio-git-0.9.9.1-6-g41dbd93-linux-ubuntu-precise-x64.deb")
        self.assertEquals(actual, expected)
