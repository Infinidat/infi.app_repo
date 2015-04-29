"""Application Repository Management Tool

Usage:
    app_repo [options] package list
    app_repo [options] package remote-list
    app_repo [options] package pull <package> [<version> [<platform> [<arch>]]]

Options:
    -f --file=CONFIGFILE     Use this config file [default: data/config.json]
    --index=INDEX            Index name [default: main-stable]
    --remote-server          Remote server name [default: repo.infinidat.com]
    --remote-index           Remote index name [default: main-stable]
    -h --help                show this screen.
    -v --version             show version.
"""


from sys import argv
from infi.pyutils.contexts import contextmanager
from infi.pyutils.decorators import wraps
from logging import getLogger
from . import extended



logger = getLogger(__name__)
bypass_console_script_logging = True # we want to use the functions in this module in the tests but without the logging stuff


def app_repo(argv=argv[1:]):
    extended.bypass_console_script_logging()
    args = extended.docopt(__doc__, argv)
    config = extended.get_config(args)

    if args['package'] and args['list']:
        return extended.show_packages(config, args['--index'])
    elif args['package'] and args['remote-list']:
        return extended.show_remote_packages(config, args['--remote-server'], args['--remote-index'])
    elif args['package'] and args['pull']:
        from .sync import pull_packages
        pull_packages = extended.console_script(name="app_repo_pull")(pull_packages)
        return pull_packages(config, args['--index'], args['--remote-server-'], args['--remote-index'],
                             args['<package>'], args['<version>'] or 'latest', args['<platform>'], args['<arch>'])


