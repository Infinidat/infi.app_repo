from .base import Indexer
from infi.gevent_utils.os import path
from infi.gevent_utils.glob import glob
from infi.gevent_utils.deferred import create_threadpool_executed_func
from infi.app_repo.utils import ensure_directory_exists, path, hard_link_or_raise_exception
from infi.gevent_utils.json_utils import encode
from infi.app_repo.filename_parser import parse_filepath, FilenameParsingFailed
from pkg_resources import parse_version
from munch import Munch


YUM_INSTALL_COMMAND = 'sudo yum install -y {0}'
YUM_UPGRADE_COMMAND = 'sudo yum makecache; sudo yum update -y {0}'

APT_INSTALL_COMMAND = 'sudo apt-get install -y {0}'
APT_UGPRADE_COMMAND = 'sudo apt-get update; sudo apt-get install -y {0}'


@create_threadpool_executed_func
def ensure_packages_json_file_exists_in_directory(dirpath):
    filepath = path.join(dirpath, 'packages.json')
    if path.exists(filepath):
        try:
            with open(filepath) as fd:
                if isinstance(encode(fd.read()), list):
                    return
        except:
            pass
    with open(filepath, 'w') as fd:
        fd.write('[]')


@create_threadpool_executed_func
def write_file(dirpath, filename, contents):
    filepath = path.join(dirpath, filename)
    with open(filepath, 'w') as fd:
        fd.write(contents)


class PrettyIndexer(Indexer): # TODO implement this
    INDEX_TYPE = 'wget'

    def initialise(self):
        ensure_directory_exists(self.base_directory)
        ensure_packages_json_file_exists_in_directory(self.base_directory)

    def are_you_interested_in_file(self, filepath, platform, arch):
        try:
            package_name, package_version, platform_string, architecture, extension = parse_filepath(filepath)
        except FilenameParsingFailed:
            return False
        if package_name == 'python':
            return False
        return True

    def consume_file(self, filepath, platform, arch):
        package_name, package_version, platform_string, architecture, extension = parse_filepath(filepath)
        platform_string = "vmware-esx" if extension == "ova" else platform_string # TODO this needs to change in our build
        dirpath = path.join(self.base_directory, 'packages', package_name, 'releases', package_version,
                            'distributions', platform_string, 'architectures', architecture,
                            'extensions', extension)
        ensure_directory_exists(dirpath)
        hard_link_or_raise_exception(filepath, dirpath)
        self.rebuild_index()

    def _normalize_url(self, dirpath):
        return dirpath.replace(self.config.artifacts_directory, '')

    def _iter_packages(self):
        for package_dirpath in glob(path.join(self.base_directory, 'packages', '*')):
            yield Munch(abspath=package_dirpath,
                        product_name=None,
                        name=path.basename(package_dirpath),
                        releases_uri=self._normalize_url(path.join(package_dirpath, 'releases.json')))

    def _iter_releases(self, package):
        for version_dirpath in glob(path.join(package.abspath, 'releases', '*')):
            release = Munch(version=path.basename(version_dirpath),
                            abspath=version_dirpath,
                            release_notes_url=None,
                            installation_instructions=Munch(install=dict(), upgrade=dict()))
            yield release

    def _iter_distributions(self, package, release):
        for distribution_dirpath in glob(path.join(release.abspath, 'distributions', '*')):
            for arch_dirpath in glob(path.join(distribution_dirpath, 'architectures', '*')):
                for extension_dirpath in glob(path.join(arch_dirpath, 'extensions', '*')):
                    [filepath] = list(glob(path.join(extension_dirpath, '*')))
                    distribution = Munch(platform=path.basename(distribution_dirpath),
                                         architecture=path.basename(arch_dirpath),
                                         extension=path.basename(extension_dirpath),
                                         filepath=self._normalize_url(filepath))
                    yield distribution

    def _get_latest_release(self, releases):
        return sorted(releases, key=lambda release: parse_version(release.version))[-1] if releases else None

    def _get_installation_instructions(self, package, release):
        installation_instructions = {}
        platforms = {distribution.platform for distribution in release.distributions}

        for distribution in release.distributions:
            for yum_platform in ('redhat', 'centos', 'oracle'):
                if yum_platform in distribution.platform:
                    installation_instructions[yum_platform] = dict(upgrade=dict(command=YUM_UPGRADE_COMMAND.format(package)),
                                                                   install=dict(command=YUM_INSTALL_COMMAND.format(package)))
            for apt_platform in ('ubuntu', ):
                if apt_platform in distribution.platform:
                    installation_instructions[apt_platform] = dict(upgrade=dict(command=APT_INSTALL_COMMAND.format(package)),
                                                                   install=dict(command=APT_UGPRADE_COMMAND.format(package)))
            if distribution.platform == 'windows':
                platform = 'windows-%s' % distribution.architecture
                installation_instructions[platform] = dict(upgrade=dict(download_link=distribution.filepath),
                                                           install=dict(download_link=distribution.filepath))
            elif distribution.platform == 'vmware-esx' and extension == 'ova':
                installation_instructions['vmware'] = dict(upgrade=dict(download_link=distribution.filepath,
                                                                        notes=["Upgrade the appliance through vCenter by using the VMware Update Manager Plug-in",
                                                                               "If vCenter does not have internet connectivity to this repository, you can download a ZIP/ISO update file from the list below and upload it to the VMware Update Manager"]),
                                                           install=dict(download_link=distribution.filepath))
        return installation_instructions

    def rebuild_index(self):
        packages = []
        for package in self._iter_packages():
            releases = []
            for release in self._iter_releases(package):
                release.distributions = list(self._iter_distributions(package, release))
                releases.append(release)
            write_file(package.abspath, 'releases.json', encode(releases, indent=4, large_object=True))

            latest_release = self._get_latest_release(releases)
            if latest_release:
                package.latest_version = latest_release.version
                package.installation_instructions = self._get_installation_instructions(package, latest_release)
                packages.append(package)
        write_file(self.base_directory, 'packages.json', encode(packages, indent=4, large_object=True))
