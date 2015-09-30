import os
import flask
import pkg_resources
import mimetypes
from infi.pyutils.lazy import cached_function
from .auth import requires_auth
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
        if app_repo_config.webserver.support_legacy_uris:
            self._register_legacy()
        mimetypes.add_type('application/json', '.json')
        return self

    def _register_blueprints(self):
        from flask.ext.autoindex import AutoIndex

        def _directory_index():
            packages = flask.Blueprint("packages", __name__)
            AutoIndex(packages, browse_root=self.app_repo_config.packages_directory)
            self.register_blueprint(packages, url_prefix="/packages")

        def _setup_script():
            self.route("/setup/<index_name>")(client_setup_script)

        def _download_script():
            self.route("/download/<index_name>")(client_download_script)
            self.route("/download/<index_name>/<package>")(client_download_script)
            self.route("/download/<index_name>/<package>/<version>")(client_download_script)

        def _install_script():
            self.route("/install/<index_name>")(client_install_script)
            self.route("/install/<index_name>/<package>")(client_install_script)
            self.route("/install/<index_name>/<package>/<version>")(client_install_script)

        def _homepage():
            self.route("/home/<index_name>")(index_home_page)
            self.route("/")(default_homepage)

        _directory_index()
        _setup_script()
        _download_script()
        _install_script()
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

    def _register_legacy(self):
        from flask.ext.autoindex import AutoIndex

        def _deb():
            deb = flask.Blueprint("deb", __name__)
            AutoIndex(deb, browse_root=path.join(self.app_repo_config.artifacts_directory, 'deb'))
            self.register_blueprint(deb, url_prefix="/deb")

        def _ova_updates():
            ova = flask.Blueprint("ova", __name__)
            AutoIndex(ova, browse_root=path.join(self.app_repo_config.artifacts_directory, 'ova', 'updates'))
            self.register_blueprint(ova, url_prefix="/ova")

        def _rpm():
            rpm = flask.Blueprint("rpm", __name__)
            AutoIndex(rpm, browse_root=path.join(self.app_repo_config.artifacts_directory, 'rpm'))
            self.register_blueprint(rpm, url_prefix="/rpm")

        def _python():
            rpm = flask.Blueprint("python", __name__)
            AutoIndex(rpm, browse_root=path.join(self.app_repo_config.artifacts_directory, 'python'))
            self.register_blueprint(rpm, url_prefix="/python")

        def _archives():
            rpm = flask.Blueprint("archives", __name__)
            AutoIndex(rpm, browse_root=path.join(self.app_repo_config.artifacts_directory, 'archives'))
            self.register_blueprint(rpm, url_prefix="/archives")

        def _setup_script():
            self.route("/setup")(redirect_to_script(client_setup_script))

        def _gpg_key():
            self.route("/gpg.key")(gpg_key)

        _deb()
        _ova_updates()
        _rpm()
        _python()
        _archives()
        _setup_script()
        _gpg_key()


def client_setup_script(index_name):
    host_url = flask.request.host_url.rstrip('/')
    data = dict(host=flask.request.host.split(':')[0], host_url=host_url, index_name=index_name)
    return flask.Response(flask.render_template("setup.sh", **data), content_type='text/plain')


def client_download_script(index_name, package=None, version=None):
    host_url = flask.request.host_url.rstrip('/')
    data = dict(host=flask.request.host.split(':')[0], host_url=host_url, index_name=index_name,
                package=package, version=version)
    return flask.Response(flask.render_template("download.sh", **data), content_type='text/plain')


def client_install_script(index_name, package=None, version=None):
    host_url = flask.request.host_url.rstrip('/')
    data = dict(host=flask.request.host.split(':')[0], host_url=host_url, index_name=index_name,
                package=package, version=version)
    return flask.Response(flask.render_template("install.sh", **data), content_type='text/plain')


def redirect_to_script(func):
    def innerfunc():
        default = flask.current_app.app_repo_config.webserver.default_index
        if default:
            return func(default)
        flask.abort(404)
    innerfunc.__name__ = '{0}__{1}'.format(redirect_to_script, func.__name__)
    return innerfunc


@cached_function
def gpg_key():
    from infi.gevent_utils.os import fopen
    with fopen(path.join(flask.current_app.app_repo_config.packages_directory, 'gpg.key')) as fd:
        return flask.Response(fd.read(), content_type='application/octet-stream')


def index_home_page(index_name):
    packages_json = path.join(flask.current_app.app_repo_config.packages_directory, index_name, 'index', 'packages.json')
    data = decode(read_file(packages_json))
    host_url = flask.request.host_url.rstrip('/')
    setup_url = '%s%s' % (host_url,
                          flask.url_for("client_setup_script", index_name=index_name))
    return flask.Response(flask.render_template("home.html", packages=data, setup_url=setup_url, host_url=host_url, index_name=index_name))


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
    from flask.ext.cors import CORS
    from os import getpid

    app = FlaskApp.from_config(config)
    app.jinja_options['extensions'].append("jinja2.ext.loopcontrols")
    cors = CORS(app, send_wildcard=True)
    app_wrapper = ProxyFix(DebuggedApplication(app, True))
    args = (config.webserver.address, config.webserver.port)
    server = WSGIServer(args, app_wrapper, log=DummyWSGILogger, handler_class=WSGIHandlerWithWorkarounds)
    server.start()
    logger.info(">>> starting HTTP server on {1}:{2}, pid={0} <<<".format(getpid(), *args))
    return server

