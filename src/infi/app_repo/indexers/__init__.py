def get_indexers(config, index_name):
    from .apt import AptIndexer
    from .wget import PrettyIndexer
    from .yum import YumIndexer
    from .python import PythonIndexer
    return AptIndexer(config, index_name), PrettyIndexer(config, index_name), YumIndexer(config, index_name), PythonIndexer(config, index_name)
