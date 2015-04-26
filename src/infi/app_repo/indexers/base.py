from infi.gevent_utils.os import path


class Indexer(object):
    INDEX_TYPE = 'yum'

    def __init__(self, config, index_name):
        super(Indexer, self).__init__()
        self.config = config
        self.base_directory = path.join(self.config.packages_directory, index_name, self.INDEX_TYPE)
        self.index_name = index_name

    def are_you_interested_in_file(self, filepath, platform, arch):
        raise NotImplementedError()

    def consume_file(self, filepath, platform, arch):
        raise NotImplementedError()

    def rebuild_index(self):
        raise NotImplementedError()

    def initialise(self):
        raise NotImplementedError()

    def iter_files(self):
        raise NotImplementedError()
