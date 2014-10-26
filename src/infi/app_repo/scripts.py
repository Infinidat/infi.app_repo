"""Application Repository Management Tool

Usage:
    app_repo [options] setup (production-defaults | development-defaults)
    app_repo [options] ftp-server [--signal-upstart]
    app_repo [options] web-server [--signal-upstart]
    app_repo [options] rpc-server [--signal-upstart]
    app_repo [options] rpc-client [--style=<style>] [<method> [<arg>...]]
    app_repo [options] config show
    app_repo [options] config apply (production-defaults | development-defaults)

Options:
    -f --file=CONFIGFILE     Use this config file [default: data/config.json]
    --style=<style>          Output style [default: solarized]
"""

from sys import argv
from infi.pyutils.contexts import contextmanager
from infi.pyutils.decorators import wraps, _ipython_inspect_module
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
    from .config import Configuration
    from .install import setup_all
    args = docopt(__doc__, argv=argv, help=True)
    config = get_config(args)
    if args['config'] and args['show']:
        print config.to_json()
    elif args['config'] and args['apply']:
        config.reset_to_development_defaults() if args['development-defaults'] else None
        config.reset_to_production_defaults() if args['production-defaults'] else None
    elif args['setup']:
        config.reset_to_development_defaults() if args['development-defaults'] else None
        config.reset_to_production_defaults() if args['production-defaults'] else None
        return setup_all(config)
    elif args['web-server']:
        return web_server(config, args['--signal-upstart'])
    elif args['ftp-server']:
        return ftp_server(config, args['--signal-upstart'])
    elif args['rpc-server']:
        return rpc_server(config, args['--signal-upstart'])
    elif args['rpc-client']:
        return rpc_client(config, args['<method>'],  args['<arg...>'], args['--style'])


def get_config(args):
    from .config import Configuration
    return Configuration.from_disk(args.get("--file", Configuration.get_default_config_file()))


@console_script(name="app_repo_web")
def web_server(config, signal_upstart):
    from gevent.monkey import patch_socket
    patch_socket()

    from .webserver import start
    webserver = start(config)
    if signal_upstart:
        from infi.app_repo.upstart import signal_init_that_i_am_ready
        signal_init_that_i_am_ready()
    webserver.serve_forever()
    webserver.close()


@console_script(name="app_repo_ftp")
def ftp_server(config, signal_upstart):
    from .ftpserver import start
    ftpserver = start(config)
    if signal_upstart:
        from infi.app_repo.upstart import signal_init_that_i_am_ready
        signal_init_that_i_am_ready()
    ftpserver.serve_forever()
    ftpserver.close()


@console_script(name="app_repo_rpc")
def rpc_server(config, signal_upstart):
    from infi.rpc import Server, ZeroRPCServerTransport
    from .service import AppRepoService

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

    if signal_upstart:
        from infi.app_repo.upstart import signal_init_that_i_am_ready
        signal_init_that_i_am_ready()

    server._shutdown_event.wait()
    webserver.close()
    server.unbind()


@console_script(name="app_repo_client")
def client(config, method, arguments, style):
    from IPython import embed
    from .service import get_client

    client = get_client(config)
    from os import environ
    if arguments.get("<method>"):
        _pretty_print(getattr(client, method)(*_jsonify_arguments(*arguments)), style)
    else:
        with patched_ipython_getargspec_context(client):
            embed()


@contextmanager
def patched_ipython_getargspec_context(client):
    original = _ipython_inspect_module.getargspec

    @wraps(original)
    def patched(func):
        if hasattr(func, "rpc_call") and getattr(func, "rpc_call"):
            return client.get_rpc_ipython_argspec(getattr(func, "rpc_method_name", func.__name__))
        return original(func)
    _ipython_inspect_module.getargspec = patched
    _ipython_inspect_module.getargspec = patched
    try:
        yield
    finally:
        _ipython_inspect_module.getargspec = original


def _pretty_print(builtin_datatype, style="solarized"):
    from json import dumps
    from pygments import highlight
    from pygments.lexers import JsonLexer
    from httpie.solarized import Solarized256Style
    from pygments.formatters import Terminal256Formatter
    print highlight(dumps(builtin_datatype, indent=4), JsonLexer(),
                    Terminal256Formatter(style= Solarized256Style if style == "solarized" else style))


def _jsonify_arguments(*args):
    def _jsonify_or_string(item):
        from izbox.utils import json_utils
        try:
            return json_utils.decode(item)
        except json_utils.DecodeError:
            return item
    return [_jsonify_or_string(item) for item in args]


# def server_stop(args):
#     config = get_config(args)
#     from infi.rpc import Client, ZeroRPCClientTransport
#     transport = ZeroRPCClientTransport.create_tcp(config.rpcserver.port, config.rpcserver.address)
#     client = Client(transport)
#     client.stop()


# def create_standalone_service(args):
#     from .service import AppRepoService
#     config = get_config(args)
#     return AppRepoService(config, lambda: None)


# def dump_metadata(args):
#     from pprint import pprint
#     pprint(create_standalone_service(args).get_metadata())


# def remote_show(args):
#     from pprint import pprint
#     config = get_config(args)
#     remote = config.remote
#     method = getattr(remote, "to_python") if hasattr(remote, "to_python") else getattr(remote, "serialize")
#     pprint(method())


# def remote_set(args):
#     config = get_config(args)
#     config.remote.fqdn = args['<fqdn>']
#     config.remote.username = args['<username>']
#     config.remote.password = args['<password>']
#     config.to_disk()


# def install(args):
#     from . import ApplicationRepository
#     from .config import Configuration
#     config = Configuration()
#     app_repo = ApplicationRepository(config.base_directory)
#     app_repo.setup()


# def determine_packages_to_download(args, missing_packages, ignored_packages):
#     from pprint import pprint
#     if args['--check']:
#         if not missing_packages:
#             print 'There are no packages available'
#         else:
#             pprint(missing_packages)
#         return set([])
#     if args['--all']:
#         return set(missing_packages).union(set())
#     if args['<package>']:
#         return set(args['<package>']).intersection(missing_packages)


# @console_script(name="app_repo")
# def pull(args):
#     service = create_standalone_service(args)
#     missing_packages, ignored_packages = service.suggest_packages_to_pull()
#     packages_to_download = determine_packages_to_download(args, missing_packages, ignored_packages)
#     for package in packages_to_download:
#         service.download_package(package)
#     service.process_incoming()


# @console_script(name="app_repo")
# def hide(args):
#     packages = args['<package>']
#     service = create_standalone_service(args)
#     service.hide_packages(packages)


# @console_script(name="app_repo")
# def add(args):
#     d = args['<directory>']
#     create_standalone_service(args).process_source(d)
