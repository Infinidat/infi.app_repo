import logging
from schematics.models import Model
from schematics.types.compound import ListType
from schematics.types import StringType, IntType, BooleanType
from schematics.types.compound import ModelType
from infi.gevent_utils.os import path, pardir, makedirs, fopen
from infi.gevent_utils.json_utils import decode


def get_projectroot():
    return path.abspath(path.join(path.dirname(__file__), pardir, pardir, pardir))


def get_base_directory():
    return path.join(get_projectroot(), 'data')


class WebserverConfiguration(Model):
    address = StringType(default="127.0.0.1")
    port = IntType(default=8000)
    default_index = StringType(required=False, default="main-stable")
    support_legacy_uris = BooleanType(default=False, required=True)


class RPCServerConfiguration(Model):
    address = StringType(default="127.0.0.1")
    port = IntType(default=8001)


class FtpServerConfiguration(Model):
    address = StringType(default="127.0.0.1")
    port = IntType(default=8002)
    username = StringType(default="app_repo")
    password = StringType(default="app_repo")


class RemoteConfiguration(Model):
    address = StringType(required=True)
    username = StringType(default='')
    password = StringType(default='')
    ftp_port = IntType(default=21)
    http_port = IntType(default=80)


class PropertyMixin(object):
    @property
    def artifacts_directory(self):
        return path.join(self.base_directory, 'artifacts')

    @property
    def incoming_directory(self):
        return path.join(self.artifacts_directory, 'incoming')

    @property
    def rejected_directory(self):
        return path.join(self.artifacts_directory, 'rejected')

    @property
    def packages_directory(self):
        return path.join(self.artifacts_directory, 'packages')

    @property
    def ftpserver_counters_filepath(self):
        return path.join(self.base_directory, 'ftp_download_counters.msgpack')

    @property
    def webserver_counters_filepath(self):
        return path.join(self.base_directory, 'http_get_counters.msgpack')


class Configuration(Model, PropertyMixin):
    filepath = StringType(required=True)
    webserver = ModelType(WebserverConfiguration, required=True, default=WebserverConfiguration)
    rpcserver = ModelType(RPCServerConfiguration, required=True, default=RPCServerConfiguration)
    ftpserver = ModelType(FtpServerConfiguration, required=True, default=FtpServerConfiguration)
    remote_servers = ListType(ModelType(RemoteConfiguration), required=True,
                                        default=[RemoteConfiguration(dict(address="repo.infinidat.com"))])

    base_directory = StringType(default=get_base_directory())
    logging_level = IntType(default=logging.DEBUG)
    development_mode = BooleanType(default=True)
    production_mode = BooleanType(default=False)
    indexes = ListType(StringType(), required=True, default=['main-stable', 'main-unstable'])

    @classmethod
    def get_default_config_file(cls):
        return path.join(get_base_directory(), 'config.json')

    def to_builtins(self):
        from json import dumps
        method = getattr(self, "to_python") if hasattr(self, "to_python") else getattr(self, "serialize")
        return method()

    def to_json(self):
        from json import dumps
        method = getattr(self, "to_python") if hasattr(self, "to_python") else getattr(self, "serialize")
        return dumps(self.to_builtins(), indent=4)

    def reload_configuration_from_disk(self):
        with fopen(self.filepath) as fd:
            kwargs = decode(fd.read())
        kwargs['filepath'] = self.filepath
        for key, value in kwargs.iteritems():
            setattr(self, key, value)
        return self

    @classmethod
    def from_disk(cls, filepath):
        filepath = filepath or cls.get_default_config_file()
        if not path.exists(filepath):
            self = cls()
            self.filepath = filepath
        else:
            with fopen(filepath) as fd:
                kwargs = decode(fd.read())
                kwargs['filepath'] = filepath
                self = cls()
                for key, value in kwargs.iteritems():
                    setattr(self, key, value)

        assert self.webserver.default_index is None or self.webserver.default_index in self.indexes
        return self

    def to_disk(self):
        if not path.exists(path.dirname(self.filepath)):
            makedirs(path.dirname(self.filepath))
        with fopen(self.filepath, 'w') as fd:
            fd.write(self.to_json())

    def reset_to_development_defaults(self):
        self.webserver.address, self.webserver.port = WebserverConfiguration.address.default, WebserverConfiguration.port.default
        self.rpcserver.address, self.rpcserver.port = RPCServerConfiguration.address.default, RPCServerConfiguration.port.default
        self.ftpserver.address, self.ftpserver.port = FtpServerConfiguration.address.default, FtpServerConfiguration.port.default
        self.production_mode = False
        self.development_mode = True
        self.to_disk()

    def reset_to_production_defaults(self):
        self.webserver.address, self.webserver.port = "0.0.0.0", 80
        self.rpcserver.address, self.rpcserver.port = "127.0.0.1", 90
        self.ftpserver.address, self.ftpserver.port = "0.0.0.0", 21
        self.production_mode = True
        self.development_mode = False
        self.to_disk()

    def get_indexers(self, index_name):
        from .indexers import get_indexers
        return get_indexers(self, index_name)
