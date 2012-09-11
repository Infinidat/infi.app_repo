import cherrypy
import os
import mako.lookup
import textwrap

def get_metadata():
    from infi.app_repo import ApplicationRepository
    from infi.app_repo.scripts import REPOSITORY_BASE_DIRECTORY
    return ApplicationRepository(REPOSITORY_BASE_DIRECTORY).get_views_metadata()

class Frontend(object):
    def __init__(self):
        super(Frontend, self).__init__()
        self.template_lookup = mako.lookup.TemplateLookup(os.path.join(os.path.dirname(__file__), 'templates'))

    def index(self):
        host = cherrypy.request.headers['HOST']
        apt_url = 'http://{}/apt_source'.format(host)
        yum_url = 'http://{}/yum_repo'.format(host)
        ftp_url = 'ftp://{}'.format(host.split(':')[0])
        metadata = get_metadata()
        return self.template_lookup.get_template("home.mako").render(apt_url=apt_url, yum_url=yum_url,
                                                                     metadata=metadata, ftp_url=ftp_url)

    def apt_source(self):
        cherrypy.response.headers['Content-Type'] = 'text/plain'
        fqdn = cherrypy.request.headers['HOST'].split(':')[0]
        return self.template_lookup.get_template("apt.mako").render(fqdn=fqdn)

    def yum_repo(self):
        cherrypy.response.headers['Content-Type'] = 'text/plain'
        fqdn = cherrypy.request.headers['HOST'].split(':')[0]
        return self.template_lookup.get_template("yum.mako").render(fqdn=fqdn)

    index.exposed = True
    apt_source.exposed = True
    yum_repo.exposed = True

def start(develop=False):
    cherrypy.config['server.socket_host'] = '0.0.0.0'
    cherrypy.config['server.socket_port'] = 8080 if develop else 80
    application_config = {
                         '/static': {'tools.staticdir.on': True,
                                     'tools.staticdir.dir': os.path.join(os.path.dirname(__file__), 'static')},
                         '/favicon.ico': {'tools.staticfile.on': True,
                                          'tools.staticfile.filename': os.path.join(os.path.dirname(__file__), 'static', 'favicon.ico')},
                         }
    cherrypy.quickstart(Frontend(), config=application_config)
