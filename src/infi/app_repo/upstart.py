from infi.app_repo.utils import path, log_execute_assert_success, fopen
from infi.pyutils.contexts import contextmanager

INIT = path.join(path.sep, 'etc', 'init')
SERVICES = {"app-repo-ftp": 'ftp-server --signal-upstart --process-incoming-on-startup',
            "app-repo-web": 'web-server --signal-upstart',
            "app-repo-rpc": 'rpc-server --signal-upstart'}

TEMPLATE = """
author "INFINIDAT, Ltd."
description "INFINIDAT Host Powertools for VMware"
version {version}
chdir {chdir}
exec {exec}
expect stop
respawn
respawn limit 30 2
start on (local-filesystems and net-device-up IFACE!=lo)
stop on runlevel [016]
"""


@contextmanager
def restart_after():
    require_restart = [service for service in SERVICES if
                       path.exists(path.join(INIT, '%s.conf' % service))]
    for service in require_restart:
        log_execute_assert_success(['stop', service], allow_to_fail=True)
    yield
    for service in require_restart:
        log_execute_assert_success(['start', service])


def _install_upstart_job(service_name, commandline_arguments):
    from infi.app_repo import PROJECTROOT
    from infi.app_repo.__version__ import __version__
    script = path.join(PROJECTROOT, 'bin', 'eapp_repo')
    kwargs = {'version': __version__,
              'chdir': PROJECTROOT,
              'exec': '{} {}'.format(script, commandline_arguments).strip(),
              }
    config = TEMPLATE.format(**kwargs)
    with fopen(path.join(INIT, '%s.conf' % service_name), 'w') as fd:
        fd.write(config)


def install():  # pragma: no cover
    with restart_after():
        for service, commandline_arguments in SERVICES.items():
            _install_upstart_job(service, commandline_arguments)
    log_execute_assert_success(['initctl', 'reload-configuration'])


def signal_init_that_i_am_ready():  # pragma: no cover
    # http://upstart.ubuntu.com/cookbook/#expect-stop
    # Specifies that the job's main process will raise the SIGSTOP signal to indicate that it is ready.
    # init(8) will wait for this signal before running the job's post-start script,
    # or considering the job to be running.
    from os import getpid, kill
    from signal import SIGSTOP
    kill(getpid(), SIGSTOP)
