def get_indexers(config, index_name):
    from .apt import AptIndexer
    from .wget import PrettyIndexer
    from .yum import YumIndexer
    return AptIndexer(config, index_name), PrettyIndexer(config, index_name), YumIndexer(config, index_name)
