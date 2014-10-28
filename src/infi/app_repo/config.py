import logging
from schematics.models import Model
from schematics.types.compound import ListType
from schematics.types import StringType, IntType, BooleanType
from schematics.types.compound import ModelType
from infi.gevent_utils.os import path
from munch import Munch


def get_projectroot():
    from os import path, pardir
    return path.abspath(path.join(path.dirname(__file__), pardir, pardir, pardir))


def get_base_directory():
    from os import path
    return path.join(get_projectroot(), 'data')


class WebserverConfiguration(Model):
    address = StringType(default="127.0.0.1")
    port = IntType(default=8000)
    default_setup_index = StringType(required=False, default="main-stable")


class RPCServerConfiguration(Model):
    address = StringType(default="127.0.0.1")
    port = IntType(default=8001)


class FtpServerConfiguration(Model):
    address = StringType(default="127.0.0.1")
    port = IntType(default=8002)
    username = StringType(default="app_repo")
    password = StringType(default="app_repo")


class RemoteConfiguration(Model):
    fqdn = StringType(default="repo.infinidat.com")
    username = StringType(default="not")
    password = StringType(default="really")


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


class Configuration(Model, PropertyMixin):
    filepath = StringType(required=True)
    webserver = ModelType(WebserverConfiguration, required=True, default=WebserverConfiguration)
    rpcserver = ModelType(RPCServerConfiguration, required=True, default=RPCServerConfiguration)
    ftpserver = ModelType(FtpServerConfiguration, required=True, default=FtpServerConfiguration)
    remote = ModelType(RemoteConfiguration, required=True, default=RemoteConfiguration)

    base_directory = StringType(default=get_base_directory())
    logging_level = IntType(default=logging.DEBUG)
    development_mode = BooleanType(default=True)
    production_mode = BooleanType(default=False)
    indexes = ListType(StringType(), required=True, default=['main-stable', 'main-unstable'])

    @classmethod
    def get_default_config_file(cls):
        from os import path
        return path.join(get_base_directory(), 'config.json')

    def to_json(self):
        from json import dumps
        method = getattr(self, "to_python") if hasattr(self, "to_python") else getattr(self, "serialize")
        return dumps(method(), indent=4)

    @classmethod
    def from_disk(cls, filepath):
        from cjson import decode
        from os import path
        filepath = filepath or cls.get_default_config_file()
        if not path.exists(filepath):
            self = cls()
            self.filepath = filepath
        else:
            with open(filepath) as fd:
                kwargs = decode(fd.read())
                kwargs['filepath'] = filepath
                self = cls()
                for key, value in kwargs.iteritems():
                    setattr(self, key, value)

        assert self.webserver.default_setup_index is None or self.webserver.default_setup_index in self.indexes
        return self

    def to_disk(self):
        from os import chmod, path, makedirs, getuid, getgid, chown
        from stat import S_IRUSR, S_IWUSR
        if not path.exists(path.dirname(self.filepath)):
            makedirs(path.dirname(self.filepath))
        with open(self.filepath, 'w') as fd:
            fd.write(self.to_json())
        chmod(self.filepath, S_IWUSR | S_IRUSR)
        chown(self.filepath, getuid(), getgid())

    def reset_to_development_defaults(self):
        self.webserver = WebserverConfiguration()
        self.rpcserver = RPCServerConfiguration()
        self.ftpserver = FtpServerConfiguration()
        self.production_mode = False
        self.development_mode = True
        self.to_disk()

    def reset_to_production_defaults(self):
        self.webserver = WebserverConfiguration(dict(address="0.0.0.0", port=80))
        self.rpcserver = RPCServerConfiguration(dict(address="0.0.0.0", port=90))
        self.ftpserver = FtpServerConfiguration(dict(address="0.0.0.0", port=21))
        self.production_mode = True
        self.development_mode = False
        self.to_disk()

    def get_indexers(self, index_name):
        from .indexers import get_indexers
        return get_indexers(self, index_name)
