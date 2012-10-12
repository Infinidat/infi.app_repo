from os import path, sep, write, close, environ, listdir
from sys import stderr, argv
from logging import getLogger, DEBUG, basicConfig
from infi.traceback import traceback_decorator
from subprocess import Popen
from infi.pyutils.lazy import cached_function
from tempfile import mkstemp
from re import sub
from ConfigParser import ConfigParser

logger = getLogger(__name__)

def get_buildout_cfg():
    buildout = ConfigParser()
    buildout.read("buildout.cfg")
    return buildout

def get_project_name():
    return get_buildout_cfg().get("project", "name")

def get_product_name():
    return get_buildout_cfg().get("project", "product_name")

def get_product_name_in_one_word():
    return '-'.join([item.lower() for item in get_product_name().split()])

def get_product_uuid():
    return get_buildout_cfg().get("project", "upgrade_code")

def get_company():
    return get_buildout_cfg().get("project", "company")

def get_deb_filepath():
    [filepath] = filter(lambda item: item.endswith('deb'), listdir('parts'))
    return filepath

def get_short_version():
    from pkg_resources import parse_version
    version_numbers = []
    parsed_version = list(parse_version(get_long_version()))
    for item in parsed_version:
        if not item.isdigit():
            break
        version_numbers.append(int(item))
    while len(version_numbers) < 3:
        version_numbers.append(0)
    index = parsed_version.index(item)
    for item in parsed_version[index:]:
        if item.isdigit():
            version_numbers.append(int(item))
            break
    while len(version_numbers) < 4:
        version_numbers.append(0)
    return '.'.join([str(item) for item in  version_numbers])

def get_long_version():
    with open(path.join('src', 'infi', 'app_repo', '__version__.py')) as fd:
        content = fd.read()
        print content
        exec content
        return locals()['__version__']

VM_TEMPLATE = dict(src=path.join(path.dirname(__file__), 'vm_template.in'),
                    dst='/opt/vmware/var/lib/build/profiles/{}.xml'.format(get_project_name()))
VAPP_TEMPLATE = dict(src=path.join(path.dirname(__file__), 'vm_template.in'),
                    dst='/opt/vmware/var/lib/build/profiles/{}.xml'.format(get_project_name()))

MAKE_APPLIANCE = "/opt/vmware/share/build/vabs.pl"
SSH_KEYFILE = environ['VMWARE_STUDIO_SSH_KEY']
BUILD_HOST = "{}@{}".format(environ['VMWARE_STUDIO_USER'], environ['VMWARE_STUDIO_HOST'])

def generate_template(profile):
    """:returns: path to generated profile"""
    with open(profile['src']) as fd:
        content = fd.read()
    content = content.replace("PROJECT_NAME", get_project_name())
    content = content.replace("PRODUCT_NAME", get_product_name())
    content = content.replace("PRODUCT_SHORT_NAME", get_product_name_in_one_word())
    content = content.replace("PRODUCT_VENDOR", get_company())
    content = content.replace("SHORT_VERSION", get_short_version())
    content = content.replace("FULL_VERSION", get_long_version())
    content = content.replace("PROUDCT_UUID", get_product_uuid())
    content = content.replace("VMX_FILENAME", get_project_name())
    content = content.replace("OVA_FILENAME", get_deb_filepath().replace('.deb', ''))
    content = content.replace("DEB_PACKAGE_FILENAME", get_deb_filepath())
    content = content.replace("ROOT_PASSWORD", environ['ROOT_PASSWORD'])
    content = content.replace("PEM_URL", environ['PEM_URL'])
    content = content.replace("VCENTER_HOSTNAME", environ['VCENTER_HOSTNAME'])
    content = content.replace("VCENTER_DATASTORE", environ['VCENTER_DATASTORE'])
    content = content.replace("VCENTER_DATACENTER", environ['VCENTER_DATACENTER'])
    content = content.replace("VCENTER_CLUSTER", environ['VCENTER_CLUSTER'])
    content = content.replace("VCENTER_PASSWORD", environ['VCENTER_PASSWORD'])
    content = content.replace("VCENTER_USERNAME", environ['VCENTER_USERNAME'])
    content = content.replace("UPDATES_DIRPATH", environ['UPDATES_DIRPATH'])
    content = content.replace("REPO_HOSTNAME", environ['REPO_HOSTNAME'])
    content = content.replace("REPO_USERNAME", environ['REPO_USERNAME'])
    content = content.replace("REPO_PASSWORD", environ['REPO_PASSWORD'])
    content = content.replace("TARGETDIR", '/opt/{}/{}'.format(get_company().lower(),
                                                               get_product_name_in_one_word()))

    fd, filepath = mkstemp(text=True)
    write(fd, content)
    close(fd)
    return filepath

def override_profile_on_build_host(profile):
    src = generate_template(profile)
    args = ['scp', '-i', SSH_KEYFILE, src, '{}:{}'.format(BUILD_HOST, path.join(BUILD_HOST, profile['dst']))]
    logger.info(' '.join(args))
    assert Popen(args).wait() == 0

def get_job_name():
    # in matrix jobs, JOB_NAME looks like vmware-powertools-bdist/arch=x86,clean=clean,os=ubuntu-11.10-38
    return environ.get('JOB_NAME', 'powertools').split('/')[0]

def get_build_number():
    return environ.get('BUILD_NUMBER', get_short_version())

def build_profile(profile):
    args = ['ssh', '-i', SSH_KEYFILE, BUILD_HOST,
            '{} --createbuild --verbose --profile {} --instance {}-{}'.format(MAKE_APPLIANCE, profile['dst'],
                                                                              get_job_name(), get_build_number())]
    if environ.has_key('VABS_ADDITIONAL_PARAMETERS'):
        args += environ['VABS_ADDITIONAL_PARAMETERS'].split(' ')
    logger.info(' '.join(args))
    assert Popen(args).wait() == 0

@traceback_decorator
def main(argv=argv[1:]):
    basicConfig(stream=stderr, level=DEBUG)
    vm_profile = generate_vm_template()
    vapp_profile = generate_vapp_template()
    override_profile_on_build_host(VM_TEMPLATE)
    override_profile_on_build_host(VAPP_TEMPLATE)
    build_profile(VAPP_TEMPLATE)

if __name__ == "__main__":
    main()
