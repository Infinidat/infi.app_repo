from logging import getLogger
from infi.gevent_utils.os import path, walk, link, makedirs, remove
from infi.execute import execute_assert_success, ExecutionError
from infi.pyutils.contexts import contextmanager
from fnmatch import fnmatch
from .errors import FileAlreadyExists
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


def _chdir_and_log(path):
    from infi.gevent_utils.os import chdir as _chdir
    _chdir(path)
    logger.debug("Changed directory to {!r}".format(path))


@contextmanager
def chdir(path):
    from infi.gevent_utils.os.path import abspath
    from infi.gevent_utils.os import curdir
    path = abspath(path)
    current_dir = abspath(curdir)
    _chdir_and_log(path)
    try:
        yield
    finally:
        _chdir_and_log(current_dir)


@contextmanager
def temporary_directory_context():
    from infi.gevent_utils.tempfile import mkdtemp
    from infi.gevent_utils.shutil import rmtree
    tempdir = mkdtemp()
    try:
        with chdir(tempdir):
            yield tempdir
    finally:
        rmtree(tempdir, ignore_errors=True)


@contextmanager
def with_tempfile():
    from tempfile import mkstemp
    from os import close, remove
    fd, path = mkstemp()  # TODO gevent-aware
    close(fd)
    try:
        yield path
    finally:
        remove(path)


def hard_link_or_raise_exception(src, dst):
    if not path.exists(dst):
        link(src, dst)
    elif path.isfile(dst):
        raise FileAlreadyExists()
    elif path.isdir(dst):
        link(src, path.join(dst, path.basename(src)))

def hard_link_and_override(src, dst):
    if not path.exists(dst):
        link(src, dst)
    elif path.isfile(dst):
        remove(dst)
        link(src, dst)
    elif path.isdir(dst):
        link(src, path.join(dst, path.basename(src)))


def ensure_directory_exists(dirpath):
    if not path.exists(dirpath):
        makedirs(dirpath)
