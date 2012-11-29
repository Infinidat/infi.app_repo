
TEMPLATE = """
author "Infinidat, Ltd."
description "Infinidat Application Repository"
version {version}
chdir {chdir}
exec {exec}
expect stop
respawn
respawn limit 5 1
start on (local-filesystems and net-device-up IFACE!=lo)
stop on runlevel [016]
"""

def install(base_directory, service_name, exec_cmd): # pragma: no cover
    from infi.app_repo import __version__
    from os.path import join, sep
    kwargs = {'version':__version__.__version__,
              'chdir':base_directory,
              'exec': exec_cmd,
              }
    config = TEMPLATE.format(**kwargs)
    with open(join(sep, 'etc', 'init', service_name + '.conf'), 'w') as fd:
        fd.write(config)

def get_executable(base_directory):
    from os.path import abspath, join, sep
    from os import pardir
    return join(abspath(join(base_directory, pardir)), 'bin', 'app_repo')

def install_webserver(base_directory):
    executable = get_executable(base_directory)
    exec_cmd = "{} -f /etc/app_repo.conf webserver start".format(executable)
    install(base_directory, "app_repo_webserver", exec_cmd)

def install_worker(base_directory):
    executable = get_executable(base_directory)
    exec_cmd = "{} -f /etc/app_repo.conf worker start --daemonize".format(executable)
    install(base_directory, "app_repo_worker", exec_cmd)

def signal_init_that_i_am_ready(): # pragma: no cover
    # http://upstart.ubuntu.com/cookbook/#expect-stop
    # Specifies that the job's main process will raise the SIGSTOP signal to indicate that it is ready.
    # init(8) will wait for this signal before running the job's post-start script,
    # or considering the job to be running.
    from os import getpid, kill
    from signal import SIGSTOP
    kill(getpid(), SIGSTOP)

