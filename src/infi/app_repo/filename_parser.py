from infi.gevent_utils.os import path
from infi.app_repo.errors import FilenameParsingFailed
from logging import getLogger
from re import match
logger = getLogger(__name__)


NAME = r"""(?P<package_name>[a-zA-Z]*[a-zA-Z\-_]+[0-9_]?[a-zA-Z\-_]+[a-zA-Z][0-9]?)"""
VERSION = r"""v?(?P<package_version>(?:[\d+\.]+)(?:-develop|-[0-9\.]+(?:_g[0-9a-f]{7})?|(?:(?:\.post\d+|\.post\d+\.|\.b\d+|\.post\d+\+|\.\d+\.|-\d+-|-develop-\d+-)(?:g[a-z0-9]{7})?))?)"""
PLATFORM = r"""(?P<platform_string>python|vmware-esx|custom|windows|aix-\d+\.\d+|solaris-\d+|linux-ubuntu-[a-z]+|linux-suse-\d+|linux-redhat-\d|linux-centos-\d|osx-\d+\.\d+|centos.el6|centos.el7|redhat.el6|redhat.el7)"""
ARCHITECTURE = r"""(?P<architecture>generic|docs|sdist|x86|x64|powerpc|sparc|x86_OVF10|x86_OVF10_UPDATE_ISO|x86_OVF10_UPDATE_ZIP|x64_OVF_10|x64_OVF_10_UPDATE_ISO|x64_OVF_10_UPDATE_ZIP|x64_dd|i686|x86_64)"""
EXTENSION = r"""(?P<extension>bin|rpm|deb|msi|pkg\.gz|tar\.gz|ova|iso|zip|img|exe||so|dll|pdb|cpp|exp)"""
TEMPLATE = r"""^{}.{}.{}.{}\.?{}$"""
FILEPATH = TEMPLATE.format(NAME, VERSION, PLATFORM, ARCHITECTURE, EXTENSION)
PLATFORM_STRING = dict(ova='vmware-esx', img='other', zip='other')
TRANSLATED_ARCHITECTURE = {"x86_64": "x64", "i686": "x86"}
TRANSLATED_PLATFORM = {"centos.el6": "linux-centos-6", "centos.el7": "linux-centos-7",
                       "redhat.el6": "linux-redhat-6", "redhat.el7": "linux-redhat-7"}


def translate_filepath(result_tuple):
    package_name, package_version, platform_string, architecture, extension = result_tuple
    return (package_name, package_version,
            TRANSLATED_PLATFORM.get(platform_string, platform_string),
            TRANSLATED_ARCHITECTURE.get(architecture, architecture),
            extension)


def parse_filepath(filepath):
    """:returns: 5-tuple (package_name, package_version, platform_string, architecture, extension)"""
    filename = path.basename(filepath)
    result = match(FILEPATH, filename)
    if result is None:
        logger.error("failed to parse {}".format(filename))
        raise FilenameParsingFailed(filepath)
    group = result.groupdict()
    return translate_filepath((group['package_name'], group['package_version'],
                               PLATFORM_STRING.get(group['extension'], group['platform_string']),
                               group['architecture'], group['extension']))
