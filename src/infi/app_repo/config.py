
import logging
import os
from schematics.models import Model
from schematics.types import StringType, IntType, BooleanType
from schematics.types.compound import ModelType

def get_projectroot():
    from os import path, pardir
    return path.abspath(path.join(path.dirname(__file__), pardir, pardir, pardir))

def get_base_directory():
    from os import path
    return path.join(get_projectroot(), 'data')

{
     '/static': {'tools.staticdir.on': True,
                 'tools.staticdir.dir': os.path.join(os.path.dirname(__file__), 'static')},
     '/assets': {'tools.staticdir.on': True,
                 'tools.staticdir.dir': os.path.join(os.path.dirname(__file__), 'assets')},
     '/favicon.ico': {'tools.staticfile.on': True,
                      'tools.staticfile.filename': os.path.join(os.path.dirname(__file__), 'static', 'favicon.ico')},
     }

def get_webserver_directory():
    from os import path
    return path.join(get_projectroot(), 'src', 'infi', 'app_repo', 'webserver')

class WebserverConfiguration(Model):
    address = StringType(default="0.0.0.0")
    port = IntType(default=80)
    daemonize = BooleanType(default=True)
    auto_reload = BooleanType(default=False)
    static_dir = StringType(default=os.path.join(get_webserver_directory(), "static"))
    assets_dir = StringType(default=os.path.join(get_webserver_directory(), "assets"))
    favicon = StringType(default=os.path.join(get_webserver_directory(), "static", "favicon.ico"))

class RemoteConfiguration(Model):
    fqdn = StringType(default="repo.infinidat.com")
    username = StringType(default="not")
    password = StringType(default="really")

class WorkerConfig(Model):
    number_of_workers = IntType(default=1)
    scheduler = BooleanType(default=True)
    process_incoming_interval = IntType(default=600)

class Configuration(Model):
    filepath = StringType(required=True)
    webserver = ModelType(WebserverConfiguration, required=True, default=WebserverConfiguration)
    worker = ModelType(WorkerConfig, required=True, default=WorkerConfig)
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
            self = cls(filepath=filepath)
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

class WebserverDevelopmentConfiguration(WebserverConfiguration):
    address = StringType(default="127.0.0.1")
    port = IntType(default=8080)
    daemonize = BooleanType(default=False)
    auto_reload = BooleanType(default=True)

class DevelopmentConfiguration(Configuration):
    webserver = ModelType(WebserverDevelopmentConfiguration, required=True, default=WebserverDevelopmentConfiguration)
    logging_level = IntType(default=logging.DEBUG)

    @classmethod
    def get_default_config_file(cls):
        from os import path
        return path.join(get_base_directory(), 'development.json')
