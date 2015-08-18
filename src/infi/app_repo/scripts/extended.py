"""Application Repository Management Tool

Usage:
    eapp_repo [options] counters show
    eapp_repo [options] config show
    eapp_repo [options] config apply (production-defaults | development-defaults)
    eapp_repo [options] setup (production-defaults | development-defaults) [--with-mock] [--with-legacy] [--force-resignature]
    eapp_repo [options] destroy [--yes]
    eapp_repo [options] ftp-server [--signal-upstart] [--process-incoming-on-startup]
    eapp_repo [options] web-server [--signal-upstart]
    eapp_repo [options] rpc-server [--signal-upstart] [--with-mock]
    eapp_repo [options] rpc-client [--style=<style>] [<method> [<arg>...]]
    eapp_repo [options] service upload-file <filepath>
    eapp_repo [options] service process-rejected-file <filepath> <platform> <arch>
    eapp_repo [options] service process-incoming <index>
    eapp_repo [options] service rebuild-index <index> [<index-type>]
    eapp_repo [options] service resign-packages
    eapp_repo [options] index list
    eapp_repo [options] index add <index>
    eapp_repo [options] index remove <index> [--yes]
    eapp_repo [options] package list
    eapp_repo [options] package remote-list <remote-server> <remote-index>
    eapp_repo [options] package pull <remote-server> <remote-index> <package> [<version> [<platform> [<arch>]]]
    eapp_repo [options] package push <remote-server> <remote-index> <package> [<version> [<platform> [<arch>]]]
    eapp_repo [options] package delete <regex> <index> [<index-type>] [(--dry-run | --yes)]
    eapp_repo [options] package cleanup <index> [(--dry-run | --yes)]

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
_bypass_console_script_logging = True # we want to use the functions in this module in the tests but without the logging stuff


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
            from logbook.concurrency import enable_gevent
            from infi.traceback import traceback_context
            from os import getpid, getuid
            from datetime import datetime
            from docopt import DocoptExit
            from sys import stderr
            import logbook
            if _bypass_console_script_logging:
                return f(*args, **kwargs)

            enable_gevent()
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


def docopt(doc, argv=None):
    from docopt import docopt as _docopt
    from infi.app_repo import DATA_DIR
    from infi.app_repo.__version__ import __version__
    return _docopt(doc.replace('default: data', 'default: %s' % DATA_DIR), argv=argv, help=True, version=__version__)


def bypass_console_script_logging():
    global _bypass_console_script_logging
    _bypass_console_script_logging = False


def eapp_repo(argv=argv[1:]):
    bypass_console_script_logging()
    args = docopt(__doc__, argv)
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
        from infi.app_repo.install import destroy_all
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
        return add_index(config, args['<index>'], args['--async'])
    elif args['index'] and args['remove'] and args['--yes']:
        return remove_index(config, args['<index>'], args['--async'])
    elif args['package'] and args['list']:
        return show_packages(config, args['--index'])
    elif args['package'] and args['remote-list']:
        return show_remote_packages(config, args['<remote-server>'], args['<remote-index>'])
    elif args['package'] and args['pull']:
        from infi.app_repo.sync import pull_packages
        pull_packages = console_script(name="app_repo_pull")(pull_packages)
        return pull_packages(config, args['--index'], args['<remote-server>'], args['<remote-index>'],
                             args['<package>'], args['<version>'], args['<platform>'], args['<arch>'])
    elif args['package'] and args['push']:
        from infi.app_repo.sync import push_packages
        push_packages = console_script(name="app_repo_push")(push_packages)
        return push_packages(config, args['--index'], args['<remote-server>'], args['<remote-index>'],
                             args.get('<package>'), args.get('<version>'), args.get('<platform>'), args.get('<arch>'))
    elif args['package'] and args['delete']:
        return delete_packages(config, build_regex_predicate(args['<regex>']), args['<index>'], args['<index-type>'],
                               args['--dry-run'], args['--yes'])
    elif args['package'] and args['cleanup']:
        return delete_old_packages(config, args['<index>'], args['--dry-run'], args['--yes'])

def get_config(args):
    from infi.app_repo.config import Configuration
    return Configuration.from_disk(args.get("--file", Configuration.get_default_config_file()))


def get_counters(config):
    from infi.app_repo.persistent_dict import PersistentDict
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
    from infi.app_repo.install import setup_all
    from infi.app_repo.mock import patch_all, empty_context
    with (patch_all if apply_mock_patches else empty_context)():
        setup_all(config, force_resignature, shell_completion=True)


@console_script(name="app_repo_web")
def web_server(config, signal_upstart):
    from gevent import monkey; monkey.patch_thread()
    from infi.app_repo.webserver import start
    webserver = start(config)
    if signal_upstart:
        from infi.app_repo.upstart import signal_init_that_i_am_ready
        signal_init_that_i_am_ready()
    webserver.serve_forever()
    webserver.close()


@console_script(name="app_repo_ftp")
def ftp_server(config, signal_upstart):
    from infi.app_repo.ftpserver import start
    ftpserver = start(config)
    if signal_upstart:
        from infi.app_repo.upstart import signal_init_that_i_am_ready
        signal_init_that_i_am_ready()
    ftpserver.serve_forever()
    ftpserver.close_all()


@console_script(name="app_repo_rpc")
def rpc_server(config, signal_upstart, apply_mock_patches):
    from infi.rpc import Server, ZeroRPCServerTransport
    from infi.app_repo.service import AppRepoService
    from infi.app_repo.mock import patch_all, empty_context
    from infi.app_repo.utils import pretty_print, jsonify_arguments
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
    from infi.app_repo.service import get_client
    from infi.app_repo.utils import pretty_print, jsonify_arguments

    client = get_client(config)
    from os import environ
    if method:
        pretty_print(getattr(client, method)(*jsonify_arguments(*arguments), async_rpc=async_rpc), style)
    else:
        with patched_ipython_getargspec_context(client):
            embed()


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
    from infi.app_repo.service import get_client
    return get_client(config).process_filepath(index, filepath, platform, arch, async_rpc=async_rpc)


def process_incoming(config, index, async_rpc=False):
    from infi.app_repo.service import get_client
    return get_client(config).process_incoming(index, async_rpc=async_rpc)


def rebuild_index(config, index, index_type, async_rpc=False):
    from infi.app_repo.service import get_client
    return get_client(config).rebuild_index(index, index_type, async_rpc=async_rpc)


def delete_old_packages(config, index, dry_run, quiet):
    from infi.app_repo.utils import pretty_print, decode, read_file, path
    packages_json = path.join(config.packages_directory, index, 'index', 'packages.json')
    data = decode(read_file(packages_json))
    for package in data:
        latest_version = package.get('latest_version', None)
        if not latest_version:
            continue

        def should_delete(filepath):
            """returns True on old releases of the package"""
            basename = path.basename(filepath)
            if not basename.startswith(package['name']):
                return False
            prefix = '{}-{}-'.format(package['name'], latest_version)
            return not basename.startswith(prefix)

        delete_packages(config, should_delete, index, None, dry_run, quiet)


def build_regex_predicate(pattern):
    import re
    return re.compile(pattern).match


def delete_packages(config, should_delete, index, index_type, dry_run, quiet):
    from infi.logging.wrappers import script_logging_context
    from infi.gevent_utils.os import path
    from infi.app_repo.service import get_client
    client = get_client(config)
    show_warning = False
    with script_logging_context(syslog=False, logfile=False, stderr=True):
        artifacts = client.get_artifacts(index, index_type)
    files_to_remove = [filepath for filepath in artifacts if should_delete(path.basename(filepath))]
    for filepath in files_to_remove:
        filepath_relative = path.relpath(filepath, config.base_directory)
        if dry_run:
            logger.debug("[dry-run] deleting {}".format(filepath_relative))
            continue
        if not quiet:
            if not raw_input('delete {} [y/N]? '.format(filepath_relative)).lower() in ('y', 'yes'):
                continue
        logger.debug("deleting {} ".format(filepath_relative))
        show_warning = True
        client.delete_artifact(filepath)
    if show_warning:
        logger.warn("do not forget to rebuild the index(es) after deleting all the packages that you wanted to delete")


def resign_packages(config, async_rpc=False):
    from infi.app_repo.service import get_client
    return get_client(config).resign_packages(async_rpc=async_rpc)


def add_index(config, index_name, async_rpc=False):
    from infi.app_repo.indexers import get_indexers
    from infi.app_repo.install import ensure_directory_exists, path
    from infi.app_repo.service import get_client
    assert index_name not in config.indexes
    for indexer in get_indexers(config, index_name):
        indexer.initialise()
    ensure_directory_exists(path.join(config.incoming_directory, index_name))
    ensure_directory_exists(path.join(config.rejected_directory, index_name))
    config.indexes.append(index_name)
    config.to_disk()
    get_client(config).reload_configuration_from_disk(async_rpc=async_rpc)



def remove_index(config, index_name, async_rpc=False):
    from infi.app_repo.indexers import get_indexers
    from infi.app_repo.utils import log_execute_assert_success
    from infi.app_repo.service import get_client
    assert index_name in config.indexes
    config.indexes = [name for name in config.indexes if name != index_name]
    config.to_disk()
    for indexer in get_indexers(config, index_name):
        log_execute_assert_success(["rm", "-rf", indexer.base_directory])
    get_client(config).reload_configuration_from_disk(async_rpc=async_rpc)


def show_packages(config, index_name):
    from infi.app_repo.utils import pretty_print, decode, read_file, path
    packages_json = path.join(config.packages_directory, index_name, 'index', 'packages.json')
    data = decode(read_file(packages_json))
    pretty_print(data)


def show_remote_packages(config, remote_host, remote_index):
    from requests import get
    from infi.app_repo.utils import pretty_print
    pretty_print(get("http://{}/packages/{}/index/packages.json".format(remote_host, remote_index)).get_json())
