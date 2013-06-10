"""Application Repository Management Tool

Usage:
  app_repo [options] webserver start
  app_repo [options] watchdog [--daemonize] start
  app_repo [options] worker [--daemonize] start
  app_repo [options] task start [--wait] <name> [--] [<remainder>...]
  app_repo [options] celery [--] [<remainder>...]
  app_repo [options] remote show
  app_repo [options] remote set <fqdn> <username> <password>
  app_repo [options] dump defaults [--development]
  app_repo [options] dump metadata
  app_repo [options] install
  app_repo [options] pull (--check | --all | <package>...)

  -f --file=CONFIGFILE     Use this config file [default: data/config.json]
"""

from sys import argv
from infi.pyutils.decorators import wraps
from logging import getLogger

logger = getLogger(__name__)


def console_script(func):
    @wraps(func)
    def decorator(*args, **kwargs):
        from logging import DEBUG, basicConfig, getLogger
        from datetime import datetime
        from infi.traceback import traceback_context
        from os import getpid, getuid
        basename = datetime.now().strftime("%Y-%m-%d.%H-%m-%S")
        filename = '/tmp/{}_{}_{}_{}.log'.format(func.__name__, basename, getpid(), getuid())
        basicConfig(level=DEBUG, filemode='w', filename=filename)
        logger.info("Logging started")
        with traceback_context():
            try:
                logger.info("Calling {}".format(func.__name__))
                result = func(*args, **kwargs)
                logger.info("Call to {} returned {}".format(func.__name__, result))
                return result
            except:
                logger.exception("Caught exception")
                raise
            finally:
                logger.info("Logging ended")
    return decorator


@console_script
def app_repo(argv=argv[1:]):
    from docopt import docopt
    args = docopt(__doc__, argv=argv, help=True)
    if args['webserver'] and args['start']:
        return webserver_start(args)
    if args['watchdog'] and args['start']:
        return watchdog_start(args)
    if args['worker'] and args['start']:
        return worker_start(args)
    if args['task'] and args['start']:
        return task_start(args)
    if args['celery']:
        init_celery(args)
        return celery(args)
    if args['dump'] and args['defaults']:
        return config_dump_defaults(args)
    if args['dump'] and args['metadata']:
        return dump_metadata(args)
    if args['remote'] and args['show']:
        return remote_show(args)
    if args['remote'] and args['set']:
        return remote_set(args)
    if args['install']:
        return install(args)
    if args['pull']:
        return pull(args)


def get_config(args):
    from ..config import Configuration
    return Configuration.from_disk(args.get("--file", Configuration.get_default_config_file()))


def config_dump_defaults(args):
    from ..config import Configuration, DevelopmentConfiguration
    config = Configuration() if not args['--development'] else DevelopmentConfiguration()
    print config.to_json()


def webserver_start(args):
    from ..webserver import start
    config = get_config(args)
    if config.webserver.daemonize:
        from infi.app_repo.upstart import signal_init_that_i_am_ready
        signal_init_that_i_am_ready()
    init_celery(args)
    start(config)


def watchdog_start(args):
    from ..watcher import start
    config = get_config(args)
    if args["--daemonize"]:
        from infi.app_repo.upstart import signal_init_that_i_am_ready
        signal_init_that_i_am_ready()
    start(config)


def worker_start(args):
    config = get_config(args)
    remainder = ['worker', '--concurrency={}'.format(config.worker.number_of_workers)]
    if config.worker.scheduler:
        remainder.append('--beat')
    if args["--daemonize"]:
        from infi.app_repo.upstart import signal_init_that_i_am_ready
        signal_init_that_i_am_ready()
    celery_args = {'--file': args.get('--file'),
                   '<remainder>': remainder}
    init_celery(args)
    celery(celery_args)


def task_start(args):
    init_celery(args)
    from .. import tasks
    task = getattr(tasks, args['<name>'])
    func = task if args['--wait'] else task.delay
    result = func(*tuple(args['<remainder>']))
    print result


def init_celery(args):
    from .. import worker
    config = get_config(args)
    worker.init(config)


def celery(args):
    from ..worker import celery
    try:
        celery.start(argv=['infi.app_repo.worker'] + args['<remainder>'])
    except SystemExit:
        pass


def dump_metadata(args):
    from ..webserver import get_metadata
    from pprint import pprint
    config = get_config(args)
    pprint(get_metadata(config['base_directory']))


def remote_show(args):
    from pprint import pprint
    config = get_config(args)
    pprint(config.remote.to_python())


def remote_set(args):
    from pprint import pprint
    config = get_config(args)
    config.remote.fqdn = args['<fqdn>']
    config.remote.username = args['<username>']
    config.remote.password = args['<password>']
    config.to_disk()


def install(args):
    from .. import ApplicationRepository
    from ..config import Configuration
    config = Configuration()
    app_repo = ApplicationRepository(config.base_directory)
    app_repo.setup()


def get_pull_view(args):
    class FakeTemplateLookup(object):

        def get_template(self, *args, **kwargs):
            return self


        def render(self, *args, **kwargs):
            return (args, kwargs)
    import cherrypy
    from ..webserver import Pull
    config = get_config(args)
    cherrypy.config['app_repo'] = config
    pull = Pull()
    pull.template_lookup = FakeTemplateLookup()
    return pull


def determine_packages_to_download(args, missing_packages, ignored_packages):
    from pprint import pprint
    if args['--check']:
        if not missing_packages:
            print 'There are no packages available'
        else:
            pprint(missing_packages)
        return
    if args['--all']:
        return set(missing_packages).union(set())
    if args['<package>']:
        return set(args['<package>']).intersection(missing_packages)


def download_packages(pull, packages_to_download):
    import cherrypy
    try:
        _, kwargs = pull.POST(*list(set(packages_to_download)))
    except cherrypy.HTTPRedirect:
        pass


def pull(args):
    pull = get_pull_view(args)
    _, kwargs = pull.GET()
    missing_packages = kwargs['missing_packages']
    ignored_packages = kwargs['ignored_packages']
    packages_to_download = determine_packages_to_download(args, missing_packages, ignored_packages)
    download_packages(pull, packages_to_download)

