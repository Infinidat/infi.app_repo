from logging import getLogger
from infi.gevent_utils.os import path, walk
from infi.execute import execute_assert_success, ExecutionError
from fnmatch import fnmatch
logger = getLogger(__name__)


def log_execute_assert_success(args, allow_to_fail=False):
    logger.info("Executing {}".format(' '.join(args)))
    try:
        return execute_assert_success(args)
    except ExecutionError:
        logger.exception("Execution failed")
        if not allow_to_fail:
            raise


def sign_rpm_package(filepath):
    from os import environ
    logger.info("Signing {!r}".format(filepath))
    command = ['rpm', '--addsign', filepath]
    logger.debug("Spawning {}".format(command))
    env = environ.copy()
    env['HOME'] = env.get('HOME', "/root")

    def _sign_rpm():
        # execute_assert_success(['rpm', '-vv', '--checksig', filepath])
        pid = spawn(command[0], command[1:], timeout=120, cwd=path.dirname(filepath), env=env)
        logger.debug("Waiting for passphrase request")
        pid.expect("Enter pass phrase:")
        pid.sendline("\n")
        logger.debug("Passphrase entered, waiting for rpm to exit")
        pid.wait() if pid.isalive() else None
        assert pid.exitstatus == 0

    from infi.gevent_utils.deferred import create_threadpool_executed_func
    create_threadpool_executed_func(_sign_rpm)()


def sign_deb_package(filepath):
    logger.info("Signing {!r}".format(filepath))
    log_execute_assert_success(['dpkg-sig', '--sign', 'builder', filepath])


def find_files(directory, pattern):
    for root, dirs, files in walk(directory):
        for basename in files:
            if fnmatch(basename, pattern):
                filename = path.join(root, basename)
                yield filename
