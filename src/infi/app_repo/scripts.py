"""Application Repository Management Tool

Usage:
    app_repo [options] counters show
    app_repo [options] config show
    app_repo [options] config apply (production-defaults | development-defaults)
    app_repo [options] setup (production-defaults | development-defaults) [--with-mock] [--with-legacy] [--force-resignature]
    app_repo [options] destroy [--yes]
    app_repo [options] ftp-server [--signal-upstart] [--process-incoming-on-startup]
    app_repo [options] web-server [--signal-upstart]
    app_repo [options] rpc-server [--signal-upstart] [--with-mock]
    app_repo [options] rpc-client [--style=<style>] [<method> [<arg>...]]
    app_repo [options] service upload-file <filepath>
    app_repo [options] service process-rejected-file <filepath> <platform> <arch>
    app_repo [options] service process-incoming <index>
    app_repo [options] service rebuild-index <index> [<index-type>]
    app_repo [options] service resign-packages
    app_repo [options] index list
    app_repo [options] index add <index>
    app_repo [options] index remove <index> [--yes]
    app_repo [options] package list
    app_repo [options] package remote-list <remote-server> <remote-index>
    app_repo [options] package pull <remote-server> <remote-index> <package> [<version> [<platform> [<arch>]]]
    app_repo [options] package push <remote-server> <remote-index> <package> [<version> [<platform> [<arch>]]]

Options:
    -f --file=CONFIGFILE     Use this config file [default: data/config.json]
    --style=STYLE            Output style [default: solarized]
    --index=INDEX            Index name [default: main-stable]
    --async                  async rpc request
    -h --help                show this screen.
    -v --version             show version.
"""

from sys import argv
from infi.pyutils.contexts import contextmanager
from infi.pyutils.decorators import wraps
from logging import getLogger

logger = getLogger(__name__)
bypass_console_script_logging = True # we want to use the functions in this module in the tests but without the logging stuff


@contextmanager
def exception_handling_context():
    from docopt import DocoptExit
    logger.info("Logging started")
    try:
        yield
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
            import logbook

            if bypass_console_script_logging:
                return f(*args, **kwargs)

            filename = '/tmp/{}.log'.format(name if name else f.__name__)
            with script_logging_context(logfile_path=filename, logfile_max_size=20*1024*1024), traceback_context(), exception_handling_context():
                logbook.set_datetime_format("local")
                logger.info("Calling {}".format(f.__name__))
                result = f(*args, **kwargs)
                logger.info("Call to {} returned {}".format(f.__name__, result))
                return result

        return decorator
    if func is None:
        return decorate
    else:
        return decorate(func)


def app_repo(argv=argv[1:]):
    from docopt import docopt
    from .config import Configuration
    from .__version__ import __version__
    from infi.app_repo import DATA_DIR
    global bypass_console_script_logging
    bypass_console_script_logging = False
    args = docopt(__doc__.replace('default: data', 'default: %s' % DATA_DIR), argv=argv, help=True, version=__version__)
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
        if args['--with-legacy']:
            config.webserver.support_legacy_uris = True
            config.to_disk()
        return setup(config, args['--with-mock'], args['--force-resignature'])
    elif args['destroy'] and args['--yes']:
        from .install import destroy_all
        destroy_all(config)
    elif args['web-server']:
        return web_server(config, args['--signal-upstart'])
    elif args['ftp-server']:
        return ftp_server(config, args['--signal-upstart'])
    elif args['rpc-server']:
        return rpc_server(config, args['--signal-upstart'], args['--with-mock'])
    elif args['rpc-client']:
        return rpc_client(config, args['<method>'], args['<arg>'], args['--style'], args['--async'])
    elif args['service'] and args['upload-file']:
        return upload_file(config, args['--index'], args['<filepath>'])
    elif args['service'] and args['process-rejected-file']:
        return process_rejected_file(config, args['--index'], args['<filepath>'],
                                     args['<platform>'], args['<arch>'], args['--async'])
    elif args['service'] and args['process-incoming']:
        return process_incoming(config, args['<index>'], args['--async'])
    elif args['service'] and args['rebuild-index']:
        return rebuild_index(config, args['<index>'], args['<index-type>'], args['--async'])
    elif args['service'] and args['resign-packages']:
        return resign_packages(config, args['--async'])
    elif args['index'] and args['list']:
        print ' '.join(config.indexes)
    elif args['index'] and args['add']:
        return add_index(config, args['<index>'])
    elif args['index'] and args['remove'] and args['--yes']:
        return remove_index(config, args['<index>'])
    elif args['package'] and args['list']:
        return show_packages(config, args['--index'])
    elif args['package'] and args['remote-list']:
        return show_remote_packages(config, args['<remote-server>'], args['<remote-index>'])
    elif args['package'] and args['pull']:
        from .sync import pull_packages
        pull_packages = console_script(name="app_repo_pull")(pull_packages)
        return pull_packages(config, args['--index'], args['<remote-server>'], args['<remote-index>'],
                             args['<package>'], args['<version>'], args['<platform>'], args['<arch>'])
    elif args['package'] and args['push']:
        from .sync import push_packages
        push_packages = console_script(name="app_repo_push")(push_packages)
        return push_packages(config, args['--index'], args['<remote-server>'], args['<remote-index>'],
                             args.get('<package>'), args.get('<version>'), args.get('<platform>'), args.get('<arch>'))


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
def setup(config, apply_mock_patches, force_resignature):
    from .install import setup_all
    from .mock import patch_all, empty_context
    with (patch_all if apply_mock_patches else empty_context)():
        setup_all(config, force_resignature, shell_completion=True)


@console_script(name="app_repo_web")
def web_server(config, signal_upstart):
    from gevent import monkey; monkey.patch_thread()
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
    from .utils import pretty_print, jsonify_arguments
    with (patch_all if apply_mock_patches else empty_context)():
        transport = ZeroRPCServerTransport.create_tcp(config.rpcserver.port, config.rpcserver.address)
        service = AppRepoService(config)

        logger.debug("binding RPC server")
        server = Server(transport, service)
        server.bind()

        if signal_upstart:
            from infi.app_repo.upstart import signal_init_that_i_am_ready
            signal_init_that_i_am_ready()

        server._shutdown_event.wait()
        server.unbind()


@console_script(name="app_repo_rpc_client")
def rpc_client(config, method, arguments, style, async_rpc=False):
    from IPython import embed
    from infi.rpc import patched_ipython_getargspec_context
    from .service import get_client
    from .utils import pretty_print, jsonify_arguments

    client = get_client(config)
    from os import environ
    if method:
        pretty_print(getattr(client, method)(*jsonify_arguments(*arguments), async_rpc=async_rpc), style)
    else:
        with patched_ipython_getargspec_context(client):
            embed()(config, filepath, index)


def upload_file(config, index, filepath):
    from ftplib import FTP
    from infi.gevent_utils.os import path, fopen
    from infi.app_repo.ftpserver import make_ftplib_gevent_friendly
    from infi.gevent_utils.deferred import create_threadpool_executed_func
    make_ftplib_gevent_friendly()
    ftp = FTP()
    ftp.connect('127.0.0.1', config.ftpserver.port)
    ftp.login(config.ftpserver.username, config.ftpserver.password)
    ftp.cwd(index)

    with fopen(filepath) as fd:
        ftp.storbinary("STOR %s" % path.basename(filepath), fd)


def process_rejected_file(config, index, filepath, platform, arch, async_rpc=False):
    from .service import get_client
    return get_client(config).process_filepath(index, filepath, platform, arch, async_rpc=async_rpc)


def process_incoming(config, index, async_rpc=False):
    from .service import get_client
    return get_client(config).process_incoming(index, async_rpc=async_rpc)


def rebuild_index(config, index, index_type, async_rpc=False):
    from .service import get_client
    return get_client(config).rebuild_index(index, index_type, async_rpc=async_rpc)


def resign_packages(config, async_rpc=False):
    from .service import get_client
    return get_client(config).resign_packages(async_rpc=async_rpc)


def add_index(config, index_name):
    from .indexers import get_indexers
    from .install import ensure_directory_exists, path
    assert index_name not in config.indexes
    for indexer in get_indexers(config, index_name):
        indexer.initialise()
    ensure_directory_exists(path.join(config.incoming_directory, index_name))
    ensure_directory_exists(path.join(config.rejected_directory, index_name))
    config.indexes.append(index_name)
    config.to_disk()


def remove_index(config, index_name):
    from .indexers import get_indexers
    from .utils import log_execute_assert_success
    assert index_name in config.indexes
    config.indexes = [name for name in config.indexes if name != index_name]
    config.to_disk()
    for indexer in get_indexers(config, index_name):
        log_execute_assert_success(["rm", "-rf", indexer.base_directory])


def show_packages(config, index_name):
    from .utils import pretty_print, decode, read_file, path
    packages_json = path.join(config.packages_directory, index_name, 'index', 'packages.json')
    data = decode(read_file(packages_json))
    pretty_print(data)


def show_remote_packages(config, remote_host, remote_index):
    from requests import get
    from .utils import pretty_print
    pretty_print(get("http://{}/packages/{}/index/packages.json".format(remote_host, remote_index)).get_json())
