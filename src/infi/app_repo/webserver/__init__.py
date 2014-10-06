from logbook import Logger
import flask
import pkg_resources
from infi.pyutils.lazy import cached_function
from flask.ext.mako import MakoTemplates, render_template

from .auth import requires_auth
from .json_response import json_response


logger = Logger(__name__)

#
# Utility functions
#


@cached_function
def get_template_folder():
    return pkg_resources.resource_filename('infi.app_repo.webserver', 'templates')


@cached_function
def get_static_folder():
    return pkg_resources.resource_filename('infi.app_repo.webserver', 'static')


def flatten_list(items):
    return [item for sublist in items for item in sublist]


def sort_by_filename(key):
    return key.split('/')[-1]


#
# Flask
#


class FlaskApp(flask.Flask):
    def setup(self, service, config):
        self.config['DEBUG'] = config.debug
        self.app_repo_base_directory = config.base_directory
        self.service = service
        self.mako = MakoTemplates(self)
app = FlaskApp(__name__, static_folder=get_static_folder(), template_folder=get_template_folder())


def are_there_new_packages_available():
    from os import path
    return path.exists(path.join(app.app_repo_base_directory, "updates_available"))


@app.route('/pull', methods=['GET'])
@requires_auth
def pull_get():
    missing_packages, ignored_packages = app.service.suggest_packages_to_pull()
    kwargs = dict(missing_packages=sorted(missing_packages, key=sort_by_filename, reverse=True),
                  ignored_packages=sorted(ignored_packages, key=sort_by_filename), reverse=True)
    return render_template("packages.mako", **kwargs)


@app.route('/pull', methods=['POST'])
@requires_auth
def pull_post():
    app.service.pull_packages([item for item, is_set in flask.request.form.iteritems() if is_set == 'on'])
    return flask.redirect(flask.url_for('queue'))


@app.route('/push', methods=['GET'])
@requires_auth
def push_get():
    missing_packages, ignored_packages = app.service.suggest_packages_to_push()
    kwargs = dict(missing_packages=sorted(missing_packages, key=sort_by_filename, reverse=True),
                  ignored_packages=sorted(ignored_packages, key=sort_by_filename), reverse=True)
    return render_template("packages.mako", **kwargs)


@app.route('/push', methods=['POST'])
@requires_auth
def push_post():
    app.service.push_packages([item for item, is_set in flask.request.form.iteritems() if is_set == 'on'])
    return flask.redirect(flask.url_for('queue'))


@app.route('/')
def index():
    host = flask.request.headers['HOST']
    setup_url = 'http://{}/setup'.format(host)
    ftp_url = 'ftp://{}/'.format(host.split(':')[0])
    metadata = app.service.get_metadata()
    metadata['packages'] = [package for package in metadata['packages'] if not package.get('hidden', None)]
    updates_available = are_there_new_packages_available()
    return render_template("home.mako", setup_url=setup_url, ftp_url=ftp_url, metadata=metadata,
                           updates_available=updates_available)


@app.route('/setup')
def setup():
    fqdn = flask.request.headers['HOST'].split(':')[0]
    return flask.Response(render_template("setup.mako", fqdn=fqdn), content_type='text/plain')


@app.route('/queue')
def queue():
    download_packages = app.service.get_queued_download_items()
    upload_packages = app.service.get_queued_upload_items()
    kwargs = dict(download_packages=download_packages, upload_packages=upload_packages)
    return render_template("queue.mako", **kwargs)


@app.route('/inventory')
@json_response
def inventory():
    return app.service.get_metadata()


def webserver_start(service, config):
    from .wsgi import DummyWSGILogger, WSGIHandlerWithWorkarounds
    from gevent.wsgi import WSGIServer
    from werkzeug.contrib.fixers import ProxyFix
    from werkzeug.debug import DebuggedApplication

    app.setup(service, config)

    app_wrapper = DebuggedApplication(app, True) if config.debug else app
    app_wrapper = ProxyFix(app_wrapper)

    server = WSGIServer((config.webserver.address, config.webserver.port), app_wrapper,
                        log=DummyWSGILogger, handler_class=WSGIHandlerWithWorkarounds)
    server.start()
    return server
