import os
import flask
import pkg_resources
from infi.pyutils.lazy import cached_function
from flask.ext.mako import MakoTemplates, render_template
from flask.ext.autoindex import AutoIndex
from .auth import requires_auth
from .json_response import json_response
from logbook import Logger
from functools import partial


logger = Logger(__name__)
TEMPLATE_FOLDER = pkg_resources.resource_filename('infi.app_repo.webserver', 'templates')
STATIC_FOLDER = pkg_resources.resource_filename('infi.app_repo.webserver', 'static')


class FlaskApp(flask.Flask):
    @classmethod
    def from_config(cls, app_repo_config):
        self = FlaskApp(__name__, static_folder=STATIC_FOLDER, template_folder=TEMPLATE_FOLDER)
        self.app_repo_config = app_repo_config
        self.config['DEBUG'] = app_repo_config.development_mode
        self.mako = MakoTemplates(self)
        self._register_blueprints()
        return self

    def _register_blueprints(self):
        def _directory_index():
            packages = flask.Blueprint("packages", __name__)
            AutoIndex(packages, browse_root=self.app_repo_config.packages_directory)
            self.register_blueprint(packages, url_prefix="/packages")

        def _setup_script():
            default = self.app_repo_config.webserver.default_setup_index
            if default:
                func = partial(client_setup_script, index_name=default)
                func.__name__ = 'client_setup_script__default'  # Flask.add_url_rule needs this
                self.route("/setup")(func)
            self.route("/setup/<index_name>")(client_setup_script)

        _directory_index()
        _setup_script()


def client_setup_script(index_name):
    fqdn = flask.request.headers['HOST'].split(':')[0]
    return flask.Response(render_template("setup.mako", fqdn=fqdn, index_name=index_name), content_type='text/plain')


def start(config):
    from .wsgi import DummyWSGILogger, WSGIHandlerWithWorkarounds
    from gevent.wsgi import WSGIServer
    from werkzeug.contrib.fixers import ProxyFix
    from werkzeug.debug import DebuggedApplication

    app = FlaskApp.from_config(config)
    app_wrapper = ProxyFix(DebuggedApplication(app, True))
    args = (config.webserver.address, config.webserver.port)
    server = WSGIServer(args, app_wrapper, log=DummyWSGILogger, handler_class=WSGIHandlerWithWorkarounds)
    server.start()
    return server


# TODO implement the pull/push mechanism
# TODO refactor the client-side code to fetch the packages json, it is no longer part of the template
