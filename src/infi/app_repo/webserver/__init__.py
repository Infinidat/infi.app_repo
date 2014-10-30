import os
import flask
import pkg_resources
import mimetypes
from infi.pyutils.lazy import cached_function
from flask.ext.autoindex import AutoIndex
from .auth import requires_auth
from .json_response import json_response
from logbook import Logger
from functools import partial
from infi.app_repo.utils import path, read_file, decode


logger = Logger(__name__)
TEMPLATE_FOLDER = pkg_resources.resource_filename('infi.app_repo.webserver', 'templates')
STATIC_FOLDER = pkg_resources.resource_filename('infi.app_repo.webserver', 'static')


class FlaskApp(flask.Flask):
    @classmethod
    def from_config(cls, app_repo_config):
        self = FlaskApp(__name__, static_folder=STATIC_FOLDER, template_folder=TEMPLATE_FOLDER)
        self.app_repo_config = app_repo_config
        self.config['DEBUG'] = app_repo_config.development_mode
        self._register_blueprints()
        self._register_counters()
        mimetypes.add_type('application/json', '.json')
        return self

    def _register_blueprints(self):
        def _directory_index():
            packages = flask.Blueprint("packages", __name__)
            AutoIndex(packages, browse_root=self.app_repo_config.packages_directory)
            self.register_blueprint(packages, url_prefix="/packages")

        def _setup_script():
            self.route("/setup/<index_name>")(client_setup_script)

        def _homepage():
            self.route("/home/<index_name>")(index_home_page)
            self.route("/")(default_homepage)

        _directory_index()
        _setup_script()
        _homepage()

    def _register_counters(self):
        from infi.app_repo.persistent_dict import PersistentDict
        def _func(response):
            if response.status_code == 200:
                key = flask.request.path
                self.counters[key] = self.counters.get(key, 0) + 1
            return response

        self.counters = PersistentDict(self.app_repo_config.webserver_counters_filepath)
        self.counters.load()
        self.after_request(_func)

def client_setup_script(index_name):
    data = dict(host=flask.request.host.split(':')[0], host_url=flask.request.host_url, index_name=index_name)
    return flask.Response(flask.render_template("setup.html", **data), content_type='text/plain')


def index_home_page(index_name):
    packages_json = path.join(flask.current_app.app_repo_config.packages_directory, index_name, 'index', 'packages.json')
    data = decode(read_file(packages_json))
    return flask.Response(flask.render_template("home.html", packages=data))


def indexes_tree():
    raise NotImplementedError()


def default_homepage():
    default = flask.current_app.app_repo_config.webserver.default_index
    if default:
        return flask.redirect(flask.url_for("index_home_page", index_name=default))
    return flask.redirect(flask.url_for("indexes_tree"))


def start(config):
    from .wsgi import DummyWSGILogger, WSGIHandlerWithWorkarounds
    from gevent.wsgi import WSGIServer
    from werkzeug.contrib.fixers import ProxyFix
    from werkzeug.debug import DebuggedApplication
    from gevent import monkey; monkey.patch_thread()

    app = FlaskApp.from_config(config)
    app_wrapper = ProxyFix(DebuggedApplication(app, True))
    args = (config.webserver.address, config.webserver.port)
    server = WSGIServer(args, app_wrapper, log=DummyWSGILogger, handler_class=WSGIHandlerWithWorkarounds)
    server.start()
    return server


# TODO implement the pull/push mechanism
# TODO refactor the client-side code to fetch the packages json, it is no longer part of the template
