import logging
from schematics.models import Model
from schematics.types import StringType, IntType, BooleanType
from schematics.types.compound import ModelType


def get_projectroot():
    from os import path, pardir
    return path.abspath(path.join(path.dirname(__file__), pardir, pardir, pardir))


def get_base_directory():
    from os import path
    return path.join(get_projectroot(), 'data')


class WebserverConfiguration(Model):
    address = StringType(default="127.0.0.1")
    port = IntType(default=8000)


class RPCServerConfiguration(Model):
    address = StringType(default="127.0.0.1")
    port = IntType(default=8001)


class RemoteConfiguration(Model):
    fqdn = StringType(default="repo.infinidat.com")
    username = StringType(default="not")
    password = StringType(default="really")


class Configuration(Model):
    filepath = StringType(required=True)
    daemonize = BooleanType(default=True)
    debug = BooleanType(default=False)
    auto_reload = BooleanType(default=False)
    webserver = ModelType(WebserverConfiguration, required=True, default=WebserverConfiguration)
    rpcserver = ModelType(RPCServerConfiguration, required=True, default=RPCServerConfiguration)
    remote = ModelType(RemoteConfiguration, required=True, default=RemoteConfiguration)
    base_directory = StringType(default=get_base_directory())
    logging_level = IntType(default=logging.INFO)

    @classmethod
    def get_default_config_file(cls):
        from os import path
        return path.join(get_base_directory(), 'config.json')

    def to_json(self):
        from json import dumps
        method = getattr(self, "to_python") if hasattr(self, "to_python") else getattr(self, "serialize")
        return dumps(method())

    @classmethod
    def from_disk(cls, filepath):
        from cjson import decode
        from os import path
        filepath = filepath or cls.get_default_config_file()
        if not path.exists(filepath):
            self = cls()
        with open(filepath) as fd:
            kwargs = decode(fd.read())
            kwargs['filepath'] = filepath
            self = cls()
            for key, value in kwargs.iteritems():
                setattr(self, key, value)
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


class DevelopmentConfiguration(Configuration):
    logging_level = IntType(default=logging.DEBUG)
    auto_reload = BooleanType(default=True)
    debug = BooleanType(default=True)

    @classmethod
    def get_default_config_file(cls):
        from os import path
        return path.join(get_base_directory(), 'development.json')
