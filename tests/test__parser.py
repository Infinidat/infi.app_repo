from unittest import TestCase
from infi.app_repo import parse_filepath


class ParserTestCase(TestCase):
    def test_host_power_tools(self):
        expected = ('host-power-tools', '0.19', 'linux-redhat-5', 'x86', 'rpm')
        actual = parse_filepath("host-power-tools-0.19-linux-redhat-5-x86.rpm")
        self.assertEquals(actual, expected)

    def test_host_power_tools__post_release(self):
        expected = ('host-power-tools', '0.19.post6.gb4c0e6d', 'linux-redhat-5', 'x86', 'rpm')
        actual = parse_filepath("host-power-tools-0.19.post6.gb4c0e6d-linux-redhat-5-x86.rpm")
        self.assertEquals(actual, expected)

    def test_infinio(self):
        expected = ('infinio-git', '0.9.9.1-6-g41dbd93', 'linux-ubuntu-precise', 'x64', 'deb')
        actual = parse_filepath("infinio-git-0.9.9.1-6-g41dbd93-linux-ubuntu-precise-x64.deb")
        self.assertEquals(actual, expected)

    def test_kernel(self):
        expected = ('kernel', '2.6.32-358.14.1', 'linux-centos-6', 'x64', 'rpm')
        actual = parse_filepath("kernel-2.6.32-358.14.1.centos.el6.x86_64.rpm")
        self.assertEquals(actual, expected)
    def test_collected_curl_json(self):
        expected = ('collectd-curl_json', '5.3.0', 'linux-centos-6', 'x64', 'rpm')
        actual = parse_filepath("collectd-curl_json-5.3.0-linux-centos-6-x64.rpm")
        self.assertEquals(actual, expected)

    def test_libcollectdclient(self):
        expected = ('libcollectdclient', '5.3.0-1', 'linux-centos-6', 'x64', 'rpm')
        actual = parse_filepath("libcollectdclient-5.3.0-1.centos.el6.x86_64.rpm")
        self.assertEquals(actual, expected)

    def test_srvadmin_racadm5(self):
        expected = ('srvadmin-racadm5', '7.3.0-4.1.112', 'linux-centos-6', 'x64', 'rpm')
        actual = parse_filepath("srvadmin-racadm5-7.3.0-4.1.112.centos.el6.x86_64.rpm")
        self.assertEquals(actual, expected)

    def test_perlGit(self):
        expected = ('perl-Git', '1.7.11.3-1', 'linux-centos-6', 'x64', 'rpm')
        actual = parse_filepath("perl-Git-1.7.11.3-1.centos.el6.x86_64.rpm")
        self.assertEquals(actual, expected)

    def test_izbox_image(self):
        expected = ('izbox', '0.post1818.g087e319', 'other', 'x64_dd', 'img')
        actual = parse_filepath("izbox-0.post1818.g087e319-linux-centos-6-x64_dd.img")
        self.assertEquals(actual, expected)

    def test_kmod(self):
        expected = ('kmod-spl', '2.6.32-358.14.1', 'linux-centos-6', 'x64', 'rpm')
        actual = parse_filepath('kmod-spl-2.6.32-358.14.1.centos.el6.x86_64.rpm')
        self.assertEquals(actual, expected)

    def test_idiotic_zfs_versioning_scheme(self):
        expected = ('kmod-zfs', '0.6.2-19_g011c0aa', 'linux-centos-6', 'x64', 'rpm')
        actual = parse_filepath('kmod-zfs-0.6.2-19_g011c0aa-linux-centos-6-x64.rpm')
        self.assertEquals(actual, expected)
        expected = ('zfs-devel', '0.6.2-19_g011c0aa', 'linux-centos-6', 'x64', 'rpm')
        actual = parse_filepath('zfs-devel-0.6.2-19_g011c0aa-linux-centos-6-x64.rpm')
        self.assertEquals(actual, expected)
