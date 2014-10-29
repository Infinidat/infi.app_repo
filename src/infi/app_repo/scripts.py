"""Application Repository Management Tool

Usage:
    app_repo [options] counters show
    app_repo [options] config show
    app_repo [options] config apply (production-defaults | development-defaults)
    app_repo [options] setup (production-defaults | development-defaults) [--with-mock]
    app_repo [options] destroy [--yes]
    app_repo [options] ftp-server [--signal-upstart] [--process-incoming-on-startup]
    app_repo [options] web-server [--signal-upstart]
    app_repo [options] rpc-server [--signal-upstart] [--with-mock]
    app_repo [options] rpc-client [--style=<style>] [<method> [<arg>...]]
    app_repo [options] service upload-file <index> <filepath>
    app_repo [options] service process-rejected-file <filepath> [--platform=<platform>] [--arch=<arch>]
    app_repo [options] service process-incoming <index>
    app_repo [options] service rebuild-index <index>
    app_repo [options] index list
    app_repo [options] index add <index>
    app_repo [options] index remove <index> [--yes]
    app_repo [options] package list
    app_repo [options] package remove <package> <version> <platform> <arch>
    app_repo [options] package remote-list <remote-http-server> <remote-index>
    app_repo [options] package pull <remote-http-server> <remote-index> <package> <version> <platform> <arch>
    app_repo [options] package push <remote-ftp-server> <remote-index> <package> <version> <platform> <arch>

Options:
    -f --file=CONFIGFILE     Use this config file [default: data/config.json]
    --style=<style>          Output style [default: solarized]
    --index=<index>          Index name [default: main-stable]
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
            filename = '/tmp/{}.log'.format(name if name else f.__name__)
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
    from .install import destroy_all
    args = docopt(__doc__, argv=argv, help=True)
    config = get_config(args)
    if args['counters'] and args['show']:
        return show_counters(config)
    elif args['config'] and args['show']:
        print config.to_json()
    elif args['config'] and args['apply']:
        config.reset_to_development_defaults() if args['development-defaults'] else None
        config.reset_to_production_defaults() if args['production-defaults'] else None
    elif args['setup']:
        config.reset_to_development_defaults() if args['development-defaults'] else None
        config.reset_to_production_defaults() if args['production-defaults'] else None
        return setup(config, args['--with-mock'])
    elif args['destroy'] and args['--yes']:
        destroy_all(config)
    elif args['web-server']:
        return web_server(config, args['--signal-upstart'])
    elif args['ftp-server']:
        return ftp_server(config, args['--signal-upstart'])
    elif args['rpc-server']:
        return rpc_server(config, args['--signal-upstart'], args['--with-mock'])
    elif args['rpc-client']:
        return rpc_client(config, args['<method>'], args['<arg>'], args['--style'])
    elif args['service'] and ['upload-file']: # TODO implement this
        upload_file(config, args['<index>'], args['<filepath>'])
    elif args['service'] and ['process-rejected-file']: # TODO implement this
        raise NotImplementedError()
    elif args['service'] and ['process-incoming']: # TODO implement this
        raise NotImplementedError()
    elif args['service'] and ['rebuild-index']: # TODO implement this
        raise NotImplementedError()
    elif args['index'] and ['list']: # TODO implement this
        raise NotImplementedError()
    elif args['index'] and ['add']: # TODO implement this
        raise NotImplementedError()
    elif args['index'] and ['remove']: # TODO implement this
        raise NotImplementedError()
    elif args['package'] and ['list']: # TODO implement this
        raise NotImplementedError()
    elif args['package'] and ['remove']: # TODO implement this
        raise NotImplementedError()


def get_config(args):
    from .config import Configuration
    return Configuration.from_disk(args.get("--file", Configuration.get_default_config_file()))


def get_counters(config):
    from .persistent_dict import PersistentDict
    ftp_counters = PersistentDict(config.ftpserver_counters_filepath)
    ftp_counters.load()
    web_counters = PersistentDict(config.webserver_counters_filepath)
    web_counters.load()
    all_counters = {}
    all_counters.update(ftp_counters)
    for key, value in web_counters.iteritems():
        all_counters[key] = all_counters.get(key, value) + 1
    return all_counters


def show_counters(config):
    print "\n".join('{item[1]:<10}{item[0]}'.format(item=item) for
                    item in sorted(get_counters(config).iteritems(), key=lambda item: item[1], reverse=True))


@console_script(name="app_repo_setup")
def setup(config, apply_mock_patches):
    from .install import setup_all
    from .mock import patch_all, empty_context
    with (patch_all if apply_mock_patches else empty_context)():
        setup_all(config)


@console_script(name="app_repo_web")
def web_server(config, signal_upstart):
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
    ftpserver.close_all()


@console_script(name="app_repo_rpc")
def rpc_server(config, signal_upstart, apply_mock_patches):
    from infi.rpc import Server, ZeroRPCServerTransport
    from .service import AppRepoService
    from .mock import patch_all, empty_context

    def shutdown_requested():
        logger.debug("shutting down all services")
        server.request_shutdown()

    with (patch_all if apply_mock_patches else empty_context)():
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
        server.unbind()


@console_script(name="app_repo_rpc_client")
def rpc_client(config, method, arguments, style):
    from IPython import embed
    from .service import get_client

    client = get_client(config)
    from os import environ
    if method:
        _pretty_print(getattr(client, method)(*_jsonify_arguments(*arguments)), style)
    else:
        with patched_ipython_getargspec_context(client):
            embed()(config, filepath, index)


def upload_file(config, index, filepath):
    from ftplib import FTP
    from infi.gevent_utils.os import path
    from infi.app_repo.ftpserver import make_ftplib_gevent_friendly

    make_ftplib_gevent_friendly()
    ftp = FTP()
    ftp.connect('127.0.0.1', config.ftpserver.port)
    ftp.login(config.ftpserver.username, config.ftpserver.password)
    ftp.cwd(index)
    with open(filepath) as fd:
        ftp.storbinary("STOR %s" % path.basename(filepath), fd)


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
    style = Solarized256Style if style == "solarized" else style
    print highlight(dumps(builtin_datatype, indent=4), JsonLexer(), Terminal256Formatter(style=style))


def _jsonify_arguments(*args):
    def _jsonify_or_string(item):
        from izbox.utils import json_utils
        try:
            return json_utils.decode(item)
        except json_utils.DecodeError:
            return item
    return [_jsonify_or_string(item) for item in args]
