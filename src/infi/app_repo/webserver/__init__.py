import cherrypy
import os
import mako.lookup
import textwrap
import cjson
from infi.pyutils.decorators import wraps

def get_metadata(base_directory):
    from infi.app_repo import ApplicationRepository
    return ApplicationRepository(base_directory).get_views_metadata()

def download_metadata(remote):
    from urllib2 import urlopen
    from cjson import decode
    url = "ftp://{0}/metadata.json".format(remote)
    return decode(urlopen(url).read())

def check_password(real, username, password):
    from pam import authenticate
    return authenticate(username, password)

def json_response(func):
    @wraps(func)
    def callable(*args, **kwargs):
        cherrypy.response.headers['Content-Type'] = "application/json"
        error_message = None
        return_value = None
        try:
            return_value = func(*args, **kwargs)
            success = True
        except Exception, error:
            error_message = str(error)
            msg = "Caught an exception on json response on function call {} with args {!r}, kwargs {!r}"
            success = False
        return cjson.encode(dict(success=success, return_value=return_value, error_message=error_message))
    return callable


class View(object):
    def __init__(self):
        super(View, self).__init__()
        self.template_lookup = mako.lookup.TemplateLookup(os.path.join(os.path.dirname(__file__), 'templates'))

    def sort_by_filename(self, key):
        return key.split('/')[-1]

class Pull(View):
    def get_packages_to_pull(self, remote):
        from .analyser import Analyser
        analyser = Analyser(remote, cherrypy.config['app_repo']['base_directory'])
        available, ignored = analyser.suggest_packages_to_pull()
        return available, ignored

    def add_packages_to_ignorelist(self, remote, packages):
        from .analyser import Analyser
        Analyser(remote, cherrypy.config['app_repo']['base_directory']).set_packages_to_ignore_when_pulling(packages)

    def GET(self):
        remote = cherrypy.config['app_repo']['remote']['fqdn']
        missing_packages, ignored_packages = self.get_packages_to_pull(remote)
        kwargs = dict(missing_packages=sorted(missing_packages, key=self.sort_by_filename, reverse=True),
                      ignored_packages=sorted(ignored_packages, key=self.sort_by_filename), reverse=True)
        return self.template_lookup.get_template("packages.mako").render(**kwargs)

    def POST(self, *args, **kwargs):
        from os import path
        remote = cherrypy.config['app_repo']['remote']['fqdn']
        missing_packages, ignored_packages = self.get_packages_to_pull(remote)
        packages_to_download = [item for item in kwargs.keys() + list(args)
                                if item in set(missing_packages).union(set(ignored_packages))]
        packages_to_ignore = missing_packages.difference(set(packages_to_download))
        self.add_packages_to_ignorelist(remote, packages_to_ignore)
        base_directory = path.join(cherrypy.config['app_repo']['base_directory'])
        result_list = self.queue_download_jobs(remote, base_directory, packages_to_download)
        raise cherrypy.HTTPRedirect("/queue")

    def index(self, *args, **kwargs):
        method = cherrypy.request.method.upper()
        return getattr(self, method)(*args, **kwargs)

    def queue_download_jobs(self, remote, base_directory, packages):
        from ..tasks import pull_package, process_incoming
        from os import path
        result_list = []
        for package in packages:
            result = pull_package.delay(remote, base_directory, package)
            result_list.append(result)
        result = process_incoming.delay(base_directory)
        result_list.append(result)
        return result

    index.exposed = True

class Push(View):
    def __init__(self):
        super(Push, self).__init__()
        self.template_lookup = mako.lookup.TemplateLookup(os.path.join(os.path.dirname(__file__), 'templates'))

    def get_packages_to_push(self, remote):
        from .analyser import Analyser
        remote = cherrypy.config['app_repo']['remote']['fqdn']
        analyser = Analyser(remote, cherrypy.config['app_repo']['base_directory'])
        ignored = analyser.get_packages_to_ignore_when_pushing()
        available, ignored = analyser.suggest_packages_to_push()
        return available, ignored

    def add_packages_to_ignorelist(self, packages):
        from .analyser import Analyser
        remote = cherrypy.config['app_repo']['remote']['fqdn']
        Analyser(remote, cherrypy.config['app_repo']['base_directory']).set_packages_to_ignore_when_pushing(packages)

    def GET(self):
        remote = cherrypy.config['app_repo']['remote']['fqdn']
        missing_packages, ignored_packages = self.get_packages_to_push(remote)
        kwargs = dict(missing_packages=sorted(missing_packages, key=self.sort_by_filename, reverse=True),
                      ignored_packages=sorted(ignored_packages, key=self.sort_by_filename), reverse=True)
        return self.template_lookup.get_template("packages.mako").render(**kwargs)

    def POST(self, *args, **kwargs):
        from os import path
        remote = cherrypy.config['app_repo']['remote']['fqdn']
        missing_packages, ignored_packages = self.get_packages_to_push(remote)
        packages_to_upload = [item for item in kwargs.keys()
                                if item in missing_packages or item in ignored_packages]
        packages_to_ignore = missing_packages.difference(set(packages_to_upload))
        self.add_packages_to_ignorelist(packages_to_ignore)
        base_directory = cherrypy.config['app_repo']['base_directory']
        result_list = self.queue_upload_jobs(cherrypy.config['app_repo']['remote'],
                                             base_directory, packages_to_upload)
        raise cherrypy.HTTPRedirect("/queue")

    def index(self, *args, **kwargs):
        method = cherrypy.request.method.upper()
        return getattr(self, method)(*args, **kwargs)

    def queue_upload_jobs(self, remote_config, base_directory, packages):
        from ..tasks import push_package
        from os import path
        result_list = []
        for package in packages:
            filename = package.split('/')[-1].rsplit('.', 1)[0]
            display_name = "Uploading {}".format(filename)
            result = push_package.delay(remote_config['fqdn'], remote_config['username'],
                                        remote_config['password'], base_directory, package)
            result_list.append(result)
        return result_list

    index.exposed = True

class Frontend(View):
    def are_there_new_packages_available(self):
        from os import path
        return path.exists(path.join(cherrypy.config['app_repo'].base_directory, "updates_available"))

    def index(self):
        host = cherrypy.request.headers['HOST']
        setup_url = 'http://{}/setup'.format(host)
        ftp_url = 'ftp://{}'.format(host.split(':')[0])
        metadata = get_metadata(cherrypy.config['app_repo']['base_directory'])
        metadata['packages'] = [package for package in metadata['packages'] if not package.get('hidden', None)]
        updates_available = self.are_there_new_packages_available()
        return self.template_lookup.get_template("home.mako").render(setup_url=setup_url, ftp_url=ftp_url,
                                                                     metadata=metadata,
                                                                     updates_available=updates_available)

    def setup(self):
        cherrypy.response.headers['Content-Type'] = 'text/plain'
        fqdn = cherrypy.request.headers['HOST'].split(':')[0]
        return self.template_lookup.get_template("setup.mako").render(fqdn=fqdn)

    def flatten_list(self, items):
        return [item for sublist in items for item in sublist]

    def queue(self, task_id=None):
        from ..worker import celery
        active_by_worker, reserved_by_worker = celery.control.inspect().active(), celery.control.inspect().reserved()
        active_tasks = self.flatten_list(active_by_worker.values() if active_by_worker else [])
        reserved_tasks = self.flatten_list(reserved_by_worker.values() if active_by_worker else [])
        if task_id is None:
            active_tasks_ids = [task['id'] for task in active_tasks]
            all_tasks = active_tasks
            all_tasks += [task for task in reserved_tasks if task['id'] not in active_tasks_ids]
            task_ids = [task['id'] for task in all_tasks]
        else:
            task_ids = list(task_id)
        active_dict = {task['id']: task for task in active_tasks}
        reserved_dict = {task['id']: task for task in reserved_tasks}
        tasks = [active_dict.get(task_id, reserved_dict.get(task_id)) for task_id in task_ids]
        kwargs = dict(tasks=tasks)
        return self.template_lookup.get_template("queue.mako").render(**kwargs)

    @json_response
    def task(self, task_id, task_name=None):
        from celery.result import AsyncResult
        from ..worker import celery
        task = AsyncResult(task_id, app=celery, task_name=task_name)
        return dict(id=task_id, state=task.state ,status=task.status, name=task.task_name, failed=task.failed(),
                    successful=task.successful(), result=task.result, ready=task.ready())

    @json_response
    def inventory(self):
        return get_metadata(cherrypy.config['app_repo']['base_directory'])

    pull = Pull()
    push = Push()
    index.exposed = True
    setup.exposed = True
    queue.exposed = True
    task.exposed = True
    inventory.exposed = True

def start(config):
    cherrypy.config['server.socket_host'] = config.webserver.address
    cherrypy.config['server.socket_port'] = config.webserver.port
    cherrypy.config['engine.autoreload_on'] = config.webserver.auto_reload
    cherrypy.config['app_repo'] = config
    basic_auth = {
                  'tools.auth_basic.on': True,
                  'tools.auth_basic.realm': 'app_repo',
                  'tools.auth_basic.checkpassword': check_password
    }
    application_config = {
                         '/static': {'tools.staticdir.on': True,
                                     'tools.staticdir.dir': config.webserver.static_dir},
                         '/assets': {'tools.staticdir.on': True,
                                     'tools.staticdir.dir': config.webserver.assets_dir},
                         '/favicon.ico': {'tools.staticfile.on': True,
                                          'tools.staticfile.filename': config.webserver.favicon},
                         '/pull': basic_auth,
                         '/push': basic_auth,
                         }
    cherrypy.quickstart(Frontend(), config=application_config)
