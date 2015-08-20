
from .base import Indexer
from infi.gevent_utils.os import path, fopen, remove
from infi.gevent_utils.glob import glob
from infi.app_repo.utils import ensure_directory_exists, hard_link_or_raise_exception, write_file
from infi.app_repo.utils import is_really_rpm, is_really_deb
from infi.gevent_utils.json_utils import decode, encode
from infi.app_repo.filename_parser import parse_filepath, FilenameParsingFailed
from pkg_resources import parse_version
from logbook import Logger
logger = Logger(__name__)

YUM_INSTALL_COMMAND = 'sudo yum install -y {0}'
YUM_UPGRADE_COMMAND = 'sudo yum makecache; sudo yum update -y {0}'

APT_INSTALL_COMMAND = 'sudo apt-get install -y {0}'
APT_UGPRADE_COMMAND = 'sudo apt-get update; sudo apt-get install -y {0}'

ZYPPER_INSTALL_COMMAND = 'sudo zypper install -y {0}'
ZYPPER_UGPRADE_COMMAND = 'sudo zypper refresh; sudo zypper update -y {0}'

PIP_INSTALL_COMMAND = 'sudo pip install --extra-index-url ///packages/{0}/pypi {1}'
PIP_UGPRADE_COMMAND = 'sudo pip install --upgrade --extra-index-url ///packages/{0}/pypi {1}'

MANUAL_COMMAND = "curl -s ///install/{0}/{1} | sudo sh -"


def ensure_packages_json_file_exists_in_directory(dirpath):
    filepath = path.join(dirpath, 'packages.json')
    if path.exists(filepath):
        try:
            with fopen(filepath) as fd:
                if isinstance(decode(fd.read()), list):
                    return
        except:
            pass
    with fopen(filepath, 'w') as fd:
        fd.write('[]')


class PrettyIndexer(Indexer):
    INDEX_TYPE = 'index'

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
        if filepath.endswith('deb') and not is_really_deb(filepath):
            return False
        if filepath.endswith('rpm') and not is_really_rpm(filepath):
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

    def _is_hidden(self, dirpath):
        return path.exists(path.join(dirpath, 'hidden'))

    def _deduce_produce_name(self, dirpath):
        try:
            with fopen(path.join(dirpath, 'product_name')) as fd:
                return fd.read().strip()
        except:
            return ' '.join(word.capitalize() for word in path.basename(dirpath).split('-')).strip()

    def _deduce_release_notes_url(self, dirpath):
        try:
            with fopen(path.join(dirpath, 'release_notes_url')) as fd:
                return fd.read().strip()
        except:
            return None

    def _iter_packages(self):
        for package_dirpath in glob(path.join(self.base_directory, 'packages', '*')):
            yield dict(abspath=package_dirpath,
                       hidden=self._is_hidden(package_dirpath),
                       product_name=self._deduce_produce_name(package_dirpath),
                       name=path.basename(package_dirpath),
                       release_notes_url=self._deduce_release_notes_url(package_dirpath),
                       releases_uri=self._normalize_url(path.join(package_dirpath, 'releases.json',)))

    def _iter_releases(self, package):
        from os import stat
        from time import ctime
        for version_dirpath in glob(path.join(package['abspath'], 'releases', '*')):
            mod_time = stat(version_dirpath).st_mtime
            release = dict(version=path.basename(version_dirpath),
                           hidden=self._is_hidden(version_dirpath),
                           abspath=version_dirpath,
                           last_modified=ctime(mod_time) if mod_time else '')
            yield release

    def _iter_distributions(self, package, release):
        for distribution_dirpath in glob(path.join(release['abspath'], 'distributions', '*')):
            for arch_dirpath in glob(path.join(distribution_dirpath, 'architectures', '*')):
                for extension_dirpath in glob(path.join(arch_dirpath, 'extensions', '*')):
                    try:
                        [filepath] = list(glob(path.join(extension_dirpath, '*')))
                    except ValueError:
                        logger.warn("expected only one file under {}, but it is not the case".format(extension_dirpath))
                        continue
                    distribution = dict(platform=path.basename(distribution_dirpath),
                                        hidden=self._is_hidden(distribution_dirpath) or \
                                               self._is_hidden(arch_dirpath) or \
                                               self._is_hidden(extension_dirpath),
                                        architecture=path.basename(arch_dirpath),
                                        extension=path.basename(extension_dirpath),
                                        filepath=self._normalize_url(filepath))
                    yield distribution

    def _get_latest_release(self, releases):
        return sorted(releases, key=lambda release: parse_version(release['version']))[-1] if releases else None

    def _get_custom_installation_instructions(self, package):
        filepath = path.join(package['abspath'], 'installation_instructions.json')
        try:
            if not path.exists(filepath):
                return dict()
            with fopen(filepath) as fd:
                result = decode(fd.read())
                return result if isinstance(result, dict) else dict()
        except:
            logger.exception("failed to read custom installation instructions from {0}".format(filepath))
            return dict()

    def _get_installation_instructions(self, package, release):
        installation_instructions = {}
        platforms = {distribution['platform'] for distribution in release['distributions']}

        for distribution in release['distributions']:
            for yum_platform in ('redhat', 'centos', 'oracle'):
                if yum_platform in distribution['platform'] and distribution['extension'] == 'rpm':
                    installation_instructions[yum_platform] = dict(upgrade=dict(command=YUM_UPGRADE_COMMAND.format(package['name'])),
                                                                   install=dict(command=YUM_INSTALL_COMMAND.format(package['name'])))
            for apt_platform in ('ubuntu', ):
                if apt_platform in distribution['platform'] and distribution['extension'] == 'deb':
                    installation_instructions[apt_platform] = dict(upgrade=dict(command=APT_UGPRADE_COMMAND.format(package['name'])),
                                                                   install=dict(command=APT_INSTALL_COMMAND.format(package['name'])))

            for zypper_platform in ('suse', ):
                if zypper_platform in distribution['platform'] and distribution['extension'] == 'rpm':
                    installation_instructions[zypper_platform] = dict(upgrade=dict(command=ZYPPER_UGPRADE_COMMAND.format(package['name'])),
                                                                   install=dict(command=ZYPPER_INSTALL_COMMAND.format(package['name'])))

            if distribution['platform'] == 'windows' and distribution['extension'] == 'msi':
                platform = 'windows-%s' % distribution['architecture']
                installation_instructions[platform] = dict(upgrade=dict(download_link=distribution['filepath']),
                                                           install=dict(download_link=distribution['filepath']))

            elif distribution['platform'] == 'vmware-esx' and distribution['extension'] == 'ova':
                installation_instructions['vmware'] = dict(upgrade=dict(download_link=distribution['filepath'],
                                                                        notes=["Upgrade the appliance through vCenter by using the VMware Update Manager Plug-in",
                                                                               "Or by the management interface on HTTPS port 5480. Consult with the User Guide for more information."]),
                                                           install=dict(download_link=distribution['filepath']))

            elif 'solaris' in distribution['platform'] and distribution['extension'] == 'pkg.gz':
                command = MANUAL_COMMAND.format(self.index_name, package['name'])
                installation_instructions['solaris'] = dict(upgrade=dict(command=command), install=dict(command=command))
            elif 'aix' in distribution['platform'] and distribution['extension'] == 'rpm':
                command = MANUAL_COMMAND.format(self.index_name, package['name']).replace("sudo", "su root -c")
                installation_instructions['aix'] = dict(upgrade=dict(command=command), install=dict(command=command))
            elif distribution['platform'] == 'python' and distribution['architecture'] == 'sdist':
                install = PIP_INSTALL_COMMAND.format(self.index_name, package['name'])
                upgrade = PIP_UGPRADE_COMMAND.format(self.index_name, package['name'])
                installation_instructions['python'] = dict(upgrade=dict(command=upgrade), install=dict(command=install))

        custom_instructions = self._get_custom_installation_instructions(package)
        for platform in platforms:
            for instruction in ('install', 'upgrade'):
                new_instruction = custom_instructions.get(platform, dict()).get(instruction)
                if isinstance(new_instruction, basestring):
                    installation_instructions.setdefault(platform, dict())[instruction] = new_instruction
        return installation_instructions

    def iter_files(self):
        for package in self._iter_packages():
            for release in self._iter_releases(package):
                for distribution in self._iter_distributions(package, release):
                    yield path.join(self.config.artifacts_directory, distribution['filepath'].strip(path.sep))

    def rebuild_index(self):
        packages = []
        for package in self._iter_packages():
            releases = []
            for release in sorted(self._iter_releases(package), reverse=True, key=lambda release: parse_version(release['version'])):
                release['distributions'] = list(self._iter_distributions(package, release))
                if not release['distributions']:
                    continue
                releases.append(release)
            write_file(path.join(package['abspath'], 'releases.json'), encode(releases, indent=4, large_object=True))

            latest_release = self._get_latest_release(releases)
            latest_release_txt = path.join(package['abspath'], 'latest_release.txt')
            if latest_release:
                package['latest_version'] = latest_release['version']
                package['installation_instructions'] = self._get_installation_instructions(package, latest_release)
                packages.append(package)
                write_file(latest_release_txt, latest_release['version'])
            elif path.exists(latest_release_txt):
                remove(latest_release_txt)
        sorted_packages = sorted(packages, key=lambda package: package['product_name'])
        write_file(path.join(self.base_directory, 'packages.json'), encode(sorted_packages, indent=4, large_object=True))
