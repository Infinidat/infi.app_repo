from infi.app_repo.utils import path, log_execute_assert_success, fopen
from infi.pyutils.contexts import contextmanager

SYSTEMD = path.join(path.sep, 'etc', 'systemd', 'system')
SERVICES = {"app-repo-ftp": 'ftp-server --process-incoming-on-startup',
            "app-repo-web": 'web-server',
            "app-repo-rpc": 'rpc-server'}

TEMPLATE = """
[Unit]
Description=INFINIDAT app-repo server
Type=notify

[Service]
WorkingDirectory={chdir}
ExecStart={exec}
Restart=on-failure
RestartSec=2

[Install]
WantedBy=multi-user.target
"""


@contextmanager
def restart_after():
    require_restart = [service for service in SERVICES if
                       path.exists(path.join(SYSTEMD, '%s.service' % service))]
    for service in require_restart:
        log_execute_assert_success(['systemctl', 'stop', '%s.service' % service], allow_to_fail=True)
    yield
    for service in require_restart:
        log_execute_assert_success(['systemctl', 'start', '%s.service' % service])


def _install_service(service_name, commandline_arguments):
    from infi.app_repo import PROJECTROOT
    from infi.app_repo.__version__ import __version__
    script = path.join(PROJECTROOT, 'bin', 'eapp_repo')
    kwargs = {'chdir': PROJECTROOT,
              'exec': '{} {}'.format(script, commandline_arguments).strip(),
              }
    config = TEMPLATE.format(**kwargs)
    with fopen(path.join(SYSTEMD, '%s.service' % service_name), 'w') as fd:
        fd.write(config)


def install():  # pragma: no cover
    with restart_after():
        for service, commandline_arguments in SERVICES.items():
            _install_service(service, commandline_arguments)
            log_execute_assert_success(['systemctl', 'enable', '%s.service' % service])
            log_execute_assert_success(['systemctl', 'start', '%s.service' % service])
