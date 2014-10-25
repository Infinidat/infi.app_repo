from logbook import Logger
import os
import flask
import pkg_resources
from infi.pyutils.lazy import cached_function
from flask.ext.mako import MakoTemplates, render_template
from flask.ext.autoindex import AutoIndex
from .auth import requires_auth
from .json_response import json_response


logger = Logger(__name__)
TEMPLATE_FOLDER = pkg_resources.resource_filename('infi.app_repo.webserver', 'templates')
STATIC_FOLDER = pkg_resources.resource_filename('infi.app_repo.webserver', 'static')


class FlaskApp(flask.Flask):
    def setup(self, config):
        self.config['DEBUG'] = True
        self.app_repo_base_directory = config.base_directory
        self.mako = MakoTemplates(self)

        packages = flask.Blueprint("packages", __name__)
        AutoIndex(packages, browse_root=os.path.join(config.base_directory, 'packages'))
        self.register_blueprint(packages, url_prefix="/packages")


app = FlaskApp(__name__, static_folder=STATIC_FOLDER, template_folder=TEMPLATE_FOLDER)


def start(config):
    from .wsgi import DummyWSGILogger, WSGIHandlerWithWorkarounds
    from gevent.wsgi import WSGIServer
    from werkzeug.contrib.fixers import ProxyFix
    from werkzeug.debug import DebuggedApplication

    app.setup(config)
    app_wrapper = ProxyFix(DebuggedApplication(app, True))
    args = (config.webserver.address, config.webserver.port)
    server = WSGIServer(args, app_wrapper, log=DummyWSGILogger, handler_class=WSGIHandlerWithWorkarounds)
    server.start()
    return server


# TODO implement the pull/push mechanism
# TODO refactor the client-side code to fetch the packages json, it is no longer part of the template
