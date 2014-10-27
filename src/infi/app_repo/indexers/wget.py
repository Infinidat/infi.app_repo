from .base import Indexer
from infi.gevent_utils.os import path
from infi.app_repo.utils import ensure_directory_exists
from infi.gevent_utils.json_utils import encode, decode


def _ensure_packages_json_file_exists_in_directory(dirpath):
    filepath = path.join(dirpath, 'packages.json')
    if path.exists(filepath):
        try:
            with open(filepath) as fd:
                if isinstance(encode(fd.read()), list):
                    return
        except:
            pass
    with open(filepath, 'w') as fd:
        fd.write(encode([], indent=4))


class PrettyIndexer(Indexer):
    INDEX_TYPE = 'wget'

    def initialise(self):
        for item in ('stable', 'unstable'):
            dirpath = path.join(self.base_directory, item)
            ensure_directory_exists(dirpath)
            _ensure_packages_json_file_exists_in_directory(dirpath)


    # def gather_metadata_for_views(self):
    #     all_files = []
    #     all_files = [filepath for filepath in find_files(self.base_directory, '*')
    #                  if not self._exclude_filepath_from_views(filepath)
    #                  and parse_filepath(filepath) != (None, None, None, None, None)]
    #     distributions = [parse_filepath(distribution) + (distribution, ) for distribution in all_files]
    #     package_names = set([distribution[0] for distribution in distributions])
    #     hidden_package_names = self.get_hidden_packages()
    #     distributions_by_package = {package_name: [distribution for distribution in distributions
    #                                                if distribution[0] == package_name]
    #                                 for package_name in package_names}
    #     for package_name, package_distributions in sorted(distributions_by_package.items(),
    #                                                       key=lambda item: item[0]):
    #         package_versions = set([distribution[1] for distribution in package_distributions])
    #         distributions_by_version = {package_version: [dict(platform=distribution[2],
    #                                                            architecture=distribution[3],
    #                                                            extension=distribution[4],
    #                                                            filepath=distribution[5].replace(self.base_directory, ''))
    #                                                       for distribution in package_distributions
    #                                                       if distribution[1] == package_version]
    #                                     for package_version in package_versions}
    #         yield dict(name=package_name,
    #                    hidden=package_name in hidden_package_names,
    #                    display_name=' '.join([item.capitalize() for item in package_name.split('-')]),
    #                    releases=[dict(version=key, distributions=value)
    #                              for key, value in sorted(distributions_by_version.items(),
    #                                                       key=lambda item: parse_version(item[0]),
    #                                                       reverse=True)])



    # def get_views_metadata(self):
    #     filepath = path.join(self.base_directory, 'metadata.json')
    #     if not path.exists(filepath):
    #         return dict(packages=())
    #     with open(filepath) as fd:
    #         return decode(fd.read())
