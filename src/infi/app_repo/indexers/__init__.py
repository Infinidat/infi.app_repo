def get_indexers(config, index_name):
    from .apt import AptIndexer
    from .wget import PrettyIndexer
    from .yum import YumIndexer
    from .python import PythonIndexer
    from .pypi import PypiIndexer
    from .vmware_studio_updates import VmwareStudioUpdatesIndexer
    return AptIndexer(config, index_name), PrettyIndexer(config, index_name), \
           YumIndexer(config, index_name), PythonIndexer(config, index_name), \
           VmwareStudioUpdatesIndexer(config, index_name), PypiIndexer(config, index_name)
