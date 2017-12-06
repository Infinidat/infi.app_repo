
from .base import Indexer
from infi.gevent_utils.os import path, fopen, remove
from infi.gevent_utils.glob import glob
from infi.app_repo.utils import ensure_directory_exists, hard_link_or_raise_exception, write_file
from infi.app_repo.utils import is_really_rpm, is_really_deb, log_execute_assert_success
from infi.gevent_utils.json_utils import decode, encode
from infi.app_repo.filename_parser import parse_filepath, FilenameParsingFailed
from pkg_resources import parse_version
from logbook import Logger
logger = Logger(__name__)

YUM_INSTALL_COMMAND = 'sudo yum install -y {0}'
YUM_UPGRADE_COMMAND = 'sudo yum makecache; sudo yum update -y {0}'

APT_INSTALL_COMMAND = 'sudo apt-get install -y {0}'
APT_UGPRADE_COMMAND = 'sudo apt-get update; sudo apt-get install -y {0}'

ZYPPER_INSTALL_COMMAND = 'sudo zypper install -n {0}'
ZYPPER_UGPRADE_COMMAND = 'sudo zypper refresh; sudo zypper update -n {0}'

PIP_INSTALL_COMMAND = 'sudo pip install --trusted-host /// --extra-index-url ///packages/{0}/pypi {1}'
PIP_UGPRADE_COMMAND = 'sudo pip install --upgrade --trusted-host /// --extra-index-url ///packages/{0}/pypi {1}'

MANUAL_COMMAND = "curl -s ///install/{0}/{1} | sudo sh -"
SOLARIS_MANUAL_COMMAND = """curl -s ///install/{0}/{1} | su root -c "PATH=$PATH bash" -"""


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

    def _read_release_date_from_file(self, dirpath):
        from dateutil.parser import parse
        try:
            with fopen(path.join(dirpath, 'release_date')) as fd:
                release_date = fd.read().strip()
                return parse(release_date).date()
        except:
            return None

    def _iter_releases(self, package):
        from os import stat
        from time import ctime
        from datetime import date, datetime
        for version_dirpath in glob(path.join(package['abspath'], 'releases', '*')):
            mod_time = stat(version_dirpath).st_mtime
            release_date = self._read_release_date_from_file(version_dirpath) or mod_time
            release = dict(version=path.basename(version_dirpath),
                           hidden=self._is_hidden(version_dirpath),
                           abspath=version_dirpath,
                           last_modified=datetime.fromtimestamp(mod_time).isoformat() if mod_time else '',
                           last_modified_timestamp=int(mod_time) if mod_time else None,
                           release_date=date.fromtimestamp(release_date).isoformat() if release_date else '',
                           )
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
                                        filepath=self._normalize_url(filepath),
                                        filesize=path.getsize(filepath))
                    yield distribution

    def _get_latest_release(self, releases):
        def sort_by_version(release):
            import re
            # remove all "-1" or "-xx" at the end (Ubuntu deb packages)
            version = re.sub("-\d+$", "", release['version'])
            return parse_version(version)
        return sorted(releases, key=sort_by_version)[-1] if releases else None

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

    def _get_pretty_platform_name(self, distribution):
        if 'linux' in distribution['platform']:
            return distribution['platform'].split('-')[1]  # linux-<dist>-<ver>
        if distribution['platform'] == 'windows':
            return 'windows-%s' % distribution['architecture']
        if distribution['platform'] == 'vmware-esx':
            return 'vmware'
        if 'solaris' in distribution['platform']:
            return 'solaris'
        if 'aix' in distribution['platform']:
            return 'aix'
        if distribution['platform'] == 'python':
            if distribution['architecture'] == 'docs':
                return 'python-docs'
            return 'python'

    def _get_installation_instructions(self, package, release):
        installation_instructions = {}
        requires_setup = False
        platforms = {self._get_pretty_platform_name(distribution) for distribution in release['distributions']}
        platforms.discard(None)

        for distribution in release['distributions']:
            platform = self._get_pretty_platform_name(distribution)

            if platform in ('redhat', 'centos', 'oracle') and distribution['extension'] == 'rpm':
                requires_setup = True
                installation_instructions[platform] = dict(installable=True,
                                                           upgrade=dict(command=YUM_UPGRADE_COMMAND.format(package['name'])),
                                                           install=dict(command=YUM_INSTALL_COMMAND.format(package['name'])))

            if platform in ('ubuntu', ) and distribution['extension'] == 'deb':
                requires_setup = True
                installation_instructions[platform] = dict(installable=True,
                                                           upgrade=dict(command=APT_UGPRADE_COMMAND.format(package['name'])),
                                                           install=dict(command=APT_INSTALL_COMMAND.format(package['name'])))

            if platform in ('suse', ) and distribution['extension'] == 'rpm':
                requires_setup = True
                installation_instructions[platform] = dict(installable=True,
                                                           upgrade=dict(command=ZYPPER_UGPRADE_COMMAND.format(package['name'])),
                                                           install=dict(command=ZYPPER_INSTALL_COMMAND.format(package['name'])))

            if distribution['platform'] == 'windows' and distribution['extension'] == 'msi':
                requires_setup = True
                installation_instructions[platform] = dict(installable=True,
                                                           upgrade=dict(download_link=distribution['filepath']),
                                                           install=dict(download_link=distribution['filepath']))

            if platform == 'vmware' and distribution['extension'] == 'ova':
                requires_setup = True
                installation_instructions[platform] = dict(installable=True,
                                                           upgrade=dict(download_link=distribution['filepath'],
                                                                        notes=["Upgrade the appliance through vCenter by using the VMware Update Manager Plug-in",
                                                                               "Or by the management interface on HTTPS port 5480. Consult with the User Guide for more information."]),
                                                           install=dict(download_link=distribution['filepath']))

            if 'solaris' == platform and distribution['extension'] == 'pkg.gz':
                requires_setup = True
                command = SOLARIS_MANUAL_COMMAND.format(self.index_name, package['name'])
                installation_instructions[platform] = dict(installable=True, upgrade=dict(command=command), install=dict(command=command))

            if 'aix' == platform and distribution['extension'] == 'rpm':
                requires_setup = True
                command = MANUAL_COMMAND.format(self.index_name, package['name']).replace("sudo", "su root -c")
                installation_instructions[platform] = dict(installable=True, upgrade=dict(command=command), install=dict(command=command))

            if platform == 'python' and distribution['architecture'] == 'sdist':
                    requires_setup = True
                    install = PIP_INSTALL_COMMAND.format(self.index_name, package['name'])
                    upgrade = PIP_UGPRADE_COMMAND.format(self.index_name, package['name'])
                    installation_instructions[platform] = dict(installable=True, upgrade=dict(command=upgrade), install=dict(command=install))

            if platform == 'python-docs' and distribution['architecture'] == 'docs':
                installation_instructions[platform] = dict(installable=False,
                                                           upgrade=dict(download_link=distribution['filepath']),
                                                           install=dict(download_link=distribution['filepath']))

            if distribution['extension'] == 'exe':
                installation_instructions[platform] = dict(installable=False,
                                                           upgrade=dict(download_link=distribution['filepath']),
                                                           install=dict(download_link=distribution['filepath']))

        custom_instructions = self._get_custom_installation_instructions(package)
        for platform in platforms.union(set(installation_instructions.keys())):
            for instruction in ('install', 'upgrade'):
                new_instruction = custom_instructions.get(platform, dict()).get(instruction)
                if isinstance(new_instruction, basestring):
                    installation_instructions.setdefault(platform, dict())[instruction] = new_instruction
            custom_installable = custom_instructions.get(platform, dict()).get('installable')
            installation_instructions.get(platform, dict())['installable'] = custom_installable or installation_instructions.get(platform, dict()).get('installable')
        return installation_instructions, requires_setup

    def iter_files(self):
        for package in self._iter_packages():
            for release in self._iter_releases(package):
                for distribution in self._iter_distributions(package, release):
                    yield path.join(self.config.artifacts_directory, distribution['filepath'].strip(path.sep))

    def rebuild_index(self):
        packages = []
        log_execute_assert_success(['find', self.base_directory, '-type', 'd', '-empty', '-print', '-delete'])
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
                package['latest_version_release_date'] = latest_release['release_date']
                package['installation_instructions'], package['requires_setup'] = self._get_installation_instructions(package, latest_release)

                packages.append(package)
                write_file(latest_release_txt, latest_release['version'])
            elif path.exists(latest_release_txt):
                remove(latest_release_txt)
        sorted_packages = sorted(packages, key=lambda package: package['product_name'])
        write_file(path.join(self.base_directory, 'packages.json'), encode(sorted_packages, indent=4, large_object=True))
