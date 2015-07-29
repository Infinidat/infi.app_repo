from logging import getLogger
from infi.gevent_utils.os import path, walk, link, makedirs, remove, fopen
from infi.gevent_utils.json_utils import encode, decode, DecodeError
from infi.gevent_utils.deferred import create_threadpool_executed_func
from infi.gevent_utils.shutil import copyfile, copyfileobj
from infi.execute import execute_assert_success, ExecutionError
from infi.pyutils.contexts import contextmanager
from fnmatch import fnmatch
from .errors import FileAlreadyExists
logger = getLogger(__name__)


def log_execute_assert_success(args, allow_to_fail=False, **kwargs):
    logger.info("Executing {}".format(' '.join(args) if isinstance(args, (list, tuple)) else args))
    try:
        result = execute_assert_success(args, **kwargs)
        logger.info("Standard output {}".format(result.get_stdout()))
        logger.info("Standard error {}".format(result.get_stderr()))
        return result
    except ExecutionError:
        logger.exception("Execution failed")
        if not allow_to_fail:
            raise


def sign_rpm_package(filepath):

    def _rpm_addsign_rewrites_the_file(filepath):
        from os import environ
        logger.info("Signing {!r}".format(filepath))
        command = ['rpm', '--addsign', filepath]
        env = environ.copy()
        env['HOME'] = env.get('HOME', "/root")
        env['GNUPGHOME'] = path.join(env.get('HOME', "/root"), ".gnupg")
        log_execute_assert_success('echo | setsid rpm --addsign {}'.format(filepath), env=env, shell=True)

    temp_filepath = filepath + '.signed'
    copyfile(filepath, temp_filepath)
    try:
        _rpm_addsign_rewrites_the_file(temp_filepath)
        with open(temp_filepath, 'rb') as src:
            with open(filepath, 'wb') as dst:
                copyfileobj(src, dst)
    finally:
        remove(temp_filepath)


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


def hard_link_or_raise_exception(src, dst):
    if not path.exists(dst):
        link(src, dst)
        return dst
    elif path.isfile(dst):
        raise FileAlreadyExists(dst)
    elif path.isdir(dst):
        dst_abspath = path.join(dst, path.basename(src))
        if path.exists(dst_abspath):
            raise FileAlreadyExists(dst_abspath)
        link(src, dst_abspath)
        return dst_abspath


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


def pretty_print(builtin_datatype, style="solarized"):
    from pygments import highlight
    from pygments.lexers import JsonLexer
    try:
        from httpie.solarized import Solarized256Style
    except ImportError:
        try:
            from httpie.output.formatters import Solarized256Style
        except ImportError:
            from httpie.plugins import FormatterPlugin
            from httpie.output.formatters.colors import Solarized256Style
    from pygments.formatters import Terminal256Formatter
    style = Solarized256Style if style == "solarized" else style
    print highlight(encode(builtin_datatype, indent=4, large_object=True), JsonLexer(), Terminal256Formatter(style=style))


def jsonify_arguments(*args):
    def _jsonify_or_string(item):
        try:
            return decode(item)
        except DecodeError:
            return item
    return [_jsonify_or_string(item) for item in args]


@create_threadpool_executed_func
def read_file(filepath):
    """ Read the contents of a file in a gevent-friendly way """
    with fopen(filepath) as fd:
        return fd.read()


@create_threadpool_executed_func
def write_file(filepath, contents):
    with fopen(filepath, 'w') as fd:
        fd.write(contents)


def file_type_contains(filepath, output):
    try:
        return output in execute_assert_success(['file', filepath]).get_stdout()
    except ExecutionError:
        logger.exception('failed to determine file type: {0}'.format(filepath))
        return False

def is_really_rpm(filepath):
    return file_type_contains(filepath, ": RPM")


def is_really_deb(filepath):
    return file_type_contains(filepath, 'Debian binary package')
