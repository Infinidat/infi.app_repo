from infi.unittest import TestCase, parameters
from infi.app_repo import parse_filepath


cases = [
    dict(expected=('host-power-tools', '0.19', 'linux-redhat-5', 'x86', 'rpm'),
         basename="host-power-tools-0.19-linux-redhat-5-x86.rpm"),

    dict(expected=('host-power-tools', '0.19.post6.gb4c0e6d', 'linux-redhat-5', 'x86', 'rpm'),
         basename="host-power-tools-0.19.post6.gb4c0e6d-linux-redhat-5-x86.rpm"),

    dict(expected=('infinio-git', '0.9.9.1-6-g41dbd93', 'linux-ubuntu-precise', 'x64', 'deb'),
         basename="infinio-git-0.9.9.1-6-g41dbd93-linux-ubuntu-precise-x64.deb"),

    dict(expected=('kernel', '2.6.32-358.14.1', 'linux-centos-6', 'x64', 'rpm'),
         basename="kernel-2.6.32-358.14.1.centos.el6.x86_64.rpm"),

    dict(expected=('collectd-curl_json', '5.3.0', 'linux-centos-6', 'x64', 'rpm'),
         basename="collectd-curl_json-5.3.0-linux-centos-6-x64.rpm"),

    dict(expected=('libcollectdclient', '5.3.0-1', 'linux-centos-6', 'x64', 'rpm'),
         basename="libcollectdclient-5.3.0-1.centos.el6.x86_64.rpm"),

    dict(expected=('srvadmin-racadm5', '7.3.0-4.1.112', 'linux-centos-6', 'x64', 'rpm'),
         basename="srvadmin-racadm5-7.3.0-4.1.112.centos.el6.x86_64.rpm"),

    dict(expected=('perl-Git', '1.7.11.3-1', 'linux-centos-6', 'x64', 'rpm'),
         basename="perl-Git-1.7.11.3-1.centos.el6.x86_64.rpm"),

    dict(expected=('izbox', '0.post1818.g087e319', 'other', 'x64_dd', 'img'),
         basename="izbox-0.post1818.g087e319-linux-centos-6-x64_dd.img"),

    dict(expected=('kmod-spl', '2.6.32-358.14.1', 'linux-centos-6', 'x64', 'rpm'),
         basename='kmod-spl-2.6.32-358.14.1.centos.el6.x86_64.rpm'),

    dict(expected=('kmod-zfs', '0.6.2-19_g011c0aa', 'linux-centos-6', 'x64', 'rpm'),
         basename='kmod-zfs-0.6.2-19_g011c0aa-linux-centos-6-x64.rpm'),

    dict(expected=('zfs-devel', '0.6.2-19_g011c0aa', 'linux-centos-6', 'x64', 'rpm'),
         basename='zfs-devel-0.6.2-19_g011c0aa-linux-centos-6-x64.rpm'),

    dict(expected=('sg3-utils', '1.33', 'linux-ubuntu-precise', 'x86', 'deb'),
         basename='sg3-utils-1.33-linux-ubuntu-precise-x86.deb'),

    dict(expected=('sg3_utils-libs', '1.28', 'linux-redhat-6', 'x64', 'rpm'),
         basename='sg3_utils-libs-1.28-linux-redhat-6-x64.rpm'),

    dict(expected=('libdevmapper1', '2', 'linux-ubuntu-precise', 'x64', 'deb'),
         basename='libdevmapper1-2-linux-ubuntu-precise-x64.deb'),

    dict(expected=('initscripts', '9.03.38', 'linux-centos-6', 'x64', 'rpm'),
         basename='initscripts-9.03.38-linux-centos-6-x64.rpm'),

    dict(expected=('libc6', '2.15', 'linux-ubuntu-precise', 'x64', 'deb'),
         basename='libc6-2.15-linux-ubuntu-precise-x64.deb'),

    dict(expected=('lsb-base', '4.0', 'linux-ubuntu-precise', 'x86', 'deb'),
         basename='lsb-base-4.0-linux-ubuntu-precise-x86.deb'),

    dict(expected=('udev', '175', 'linux-ubuntu-precise', 'x86', 'deb'),
         basename='udev-175-linux-ubuntu-precise-x86.deb'),

    dict(expected=('kmod-mpt2sas', '14.00.00.00', 'linux-centos-6', 'x64', 'rpm'),
         basename="kmod-mpt2sas-14.00.00.00-linux-centos-6-x64.rpm"),

    dict(expected=('kmod-mpt2sas-debug', '14.00.00.00', 'linux-centos-6', 'x64', 'rpm'),
         basename="kmod-mpt2sas-debug-14.00.00.00-linux-centos-6-x64.rpm"),

    dict(expected=('mpt2sas-debuginfo', '14.00.00.00', 'linux-centos-6', 'x64', 'rpm'),
         basename="mpt2sas-debuginfo-14.00.00.00-linux-centos-6-x64.rpm"),

    dict(expected=('mpt2sas-debuginfo', '14.00.00.00.2.6.32-358.14.1', 'linux-centos-6', 'x64', 'rpm'),
         basename="mpt2sas-debuginfo-14.00.00.00.2.6.32-358.14.1-linux-centos-6-x64.rpm"),

    dict(expected=('host-power-tools-for-vmware', '1.2.6', 'vmware-esx', 'x86_OVF10', 'ova'),
         basename="host-power-tools-for-vmware-1.2.6-linux-ubuntu-lucid-x86_OVF10.ova"),

    dict(expected=('host-power-tools-for-vmware', '1.2.6', 'vmware-esx', 'x86_OVF10_UPDATE_ISO', 'iso'),
         basename="host-power-tools-for-vmware-1.2.6-vmware-esx-x86_OVF10_UPDATE_ISO.iso"),

    dict(expected=('host-power-tools-for-vmware', '1.2.6', 'vmware-esx', 'x86_OVF10_UPDATE_ZIP', 'iso'),
         basename="host-power-tools-for-vmware-1.2.6-vmware-esx-x86_OVF10_UPDATE_ZIP.iso"),
    ]

class ParserTestCase(TestCase):
    @parameters.iterate("case", [item for item in cases])
    def test_parser(self, case):
        actual = parse_filepath(case['basename'])
        self.assertEquals(actual, case['expected'])
