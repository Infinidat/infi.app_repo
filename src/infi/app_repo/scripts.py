"""Application Repository Management Tool

Usage:
  app_repo [options] server start [--no-daemonize]
  app_repo [options] server stop
  app_repo [options] remote show
  app_repo [options] remote set <fqdn> <username> <password>
  app_repo [options] dump defaults [--development]
  app_repo [options] dump metadata
  app_repo [options] install
  app_repo [options] pull (--check | --all | <package>...)
  app_repo [options] hide <package>...
  app_repo [options] add <directory>

  -f --file=CONFIGFILE     Use this config file [default: data/config.json]
"""

from sys import argv
from infi.pyutils.decorators import wraps
from logging import getLogger

logger = getLogger(__name__)


def console_script(func=None, name=None):
    def decorate(f):
        @wraps(f)
        def decorator(*args, **kwargs):
            from infi.logging.wrappers import script_logging_context
            from infi.traceback import traceback_context
            from os import getpid, getuid
            from datetime import datetime
            from docopt import DocoptExit
            from sys import stderr
            basename = datetime.now().strftime("%Y-%m-%d.%H-%m-%S")
            filename = '/tmp/{}_{}_{}_{}.log'.format(name if name else f.__name__, basename, getpid(), getuid())
            with script_logging_context(logfile_path=filename):
                logger.info("Logging started")
                with traceback_context():
                    try:
                        logger.info("Calling {}".format(f.__name__))
                        result = f(*args, **kwargs)
                        logger.info("Call to {} returned {}".format(f.__name__, result))
                        return result
                    except DocoptExit, e:
                        stderr.write(str(e) + "\n")
                        logger.info("printed usage, exitting.")
                    except SystemExit, e:
                        if e.code != 3:  # SystemExit(3) --> reloading
                            logger.exception("Caught SystemExit")
                        raise
                    except:
                        logger.exception("Caught exception")
                        raise
                    finally:
                        logger.info("Logging ended")
        return decorator
    if func is None:
        return decorate
    else:
        return decorate(func)


def app_repo(argv=argv[1:]):
    from docopt import docopt
    args = docopt(__doc__, argv=argv, help=True)
    if args['server'] and args['start']:
        return server_start(args)
    if args['server'] and args['stop']:
        return server_stop(args)
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
    if args['hide']:
        return hide(args)
    if args['add']:
        return add(args)


def get_config(args):
    from .config import Configuration
    return Configuration.from_disk(args.get("--file", Configuration.get_default_config_file()))


def config_dump_defaults(args):
    from .config import Configuration, DevelopmentConfiguration
    config = Configuration() if not args['--development'] else DevelopmentConfiguration()
    print config.to_json()


@console_script(name="app_repo")
def _server_start(config):
    from gevent.monkey import patch_socket
    patch_socket()

    from infi.rpc import Server, ZeroRPCServerTransport
    from .service import AppRepoService
    from .webserver import webserver_start

    def shutdown_requested():
        logger.debug("shutting down all services")
        server.request_shutdown()

    transport = ZeroRPCServerTransport.create_tcp(config.rpcserver.port, config.rpcserver.address)
    service = AppRepoService(config, shutdown_requested)
    logger.debug("starting service")
    service.start()

    logger.debug("binding RPC server")
    server = Server(transport, service)
    server.bind()

    logger.debug("binding web server")
    webserver = webserver_start(service, config)

    if config.daemonize:
        from infi.app_repo.upstart import signal_init_that_i_am_ready
        signal_init_that_i_am_ready()

    # TODO add a wait method on server in infi.rpc
    server._shutdown_event.wait()
    webserver.close()
    server.unbind()


def server_start(args):
    config = get_config(args)
    if args['--no-daemonize']:
        config.daemonize = False
    if config.auto_reload:
        from functools import partial
        from .reloader import run_with_reloader
        run_with_reloader(partial(_server_start, config))
    else:
        _server_start(config)


def server_stop(args):
    config = get_config(args)
    from infi.rpc import Client, ZeroRPCClientTransport
    transport = ZeroRPCClientTransport.create_tcp(config.rpcserver.port, config.rpcserver.address)
    client = Client(transport)
    client.stop()


def create_standalone_service(args):
    from .service import AppRepoService
    config = get_config(args)
    return AppRepoService(config, lambda: None)


def dump_metadata(args):
    from pprint import pprint
    pprint(create_standalone_service(args).get_metadata())


def remote_show(args):
    from pprint import pprint
    config = get_config(args)
    remote = config.remote
    method = getattr(remote, "to_python") if hasattr(remote, "to_python") else getattr(remote, "serialize")
    pprint(method())


def remote_set(args):
    config = get_config(args)
    config.remote.fqdn = args['<fqdn>']
    config.remote.username = args['<username>']
    config.remote.password = args['<password>']
    config.to_disk()


def install(args):
    from . import ApplicationRepository
    from .config import Configuration
    config = Configuration()
    app_repo = ApplicationRepository(config.base_directory)
    app_repo.setup()


def determine_packages_to_download(args, missing_packages, ignored_packages):
    from pprint import pprint
    if args['--check']:
        if not missing_packages:
            print 'There are no packages available'
        else:
            pprint(missing_packages)
        return set([])
    if args['--all']:
        return set(missing_packages).union(set())
    if args['<package>']:
        return set(args['<package>']).intersection(missing_packages)


@console_script(name="app_repo")
def pull(args):
    service = create_standalone_service(args)
    missing_packages, ignored_packages = service.suggest_packages_to_pull()
    packages_to_download = determine_packages_to_download(args, missing_packages, ignored_packages)
    for package in packages_to_download:
        service.download_package(package)
    service.process_incoming()


@console_script(name="app_repo")
def hide(args):
    packages = args['<package>']
    service = create_standalone_service(args)
    service.hide_packages(packages)


@console_script(name="app_repo")
def add(args):
    d = args['<directory>']
    create_standalone_service(args).process_source(d)
