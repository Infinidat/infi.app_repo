# Taken from werkzeug.serving and adapted for gevent and added exit on main exit.
# TODO refactor to somewhere else (gevent-utils, flask-something, whatever)
import os
import sys
import gevent
import logbook

from werkzeug._compat import iteritems, PY2, text_type

log = logbook.Logger(__name__)


def _iter_module_files():
    # The list call is necessary on Python 3 in case the module
    # dictionary modifies during iteration.
    for module in list(sys.modules.values()):
        filename = getattr(module, '__file__', None)
        if filename:
            old = None
            while not os.path.isfile(filename):
                old = filename
                filename = os.path.dirname(filename)
                if filename == old:
                    break
            else:
                if filename[-4:] in ('.pyc', '.pyo'):
                    filename = filename[:-1]
                yield filename


def _reloader_stat_loop(main_greenlet, extra_files=None, interval=1):
    """When this function is run from the main thread, it will force other
    threads to exit when any modules currently loaded change.

    Copyright notice.  This function is based on the autoreload.py from
    the CherryPy trac which originated from WSGIKit which is now dead.

    :param extra_files: a list of additional files it should watch.
    """
    from itertools import chain
    mtimes = {}
    while not main_greenlet.ready():
        for filename in chain(_iter_module_files(), extra_files or ()):
            try:
                mtime = os.stat(filename).st_mtime
            except OSError:
                continue

            old_time = mtimes.get(filename)
            if old_time is None:
                mtimes[filename] = mtime
                continue
            elif mtime > old_time:
                log.info(' * Detected change in %r, reloading' % filename)
                sys.exit(3)
        gevent.sleep(interval)
    sys.exit(0)


def restart_with_reloader():
    """Spawn a new Python interpreter with the same arguments as this one,
    but running the reloader thread.
    """
    while 1:
        log.info(' * Restarting with reloader')
        args = [sys.executable] + sys.argv
        new_environ = os.environ.copy()
        new_environ['WERKZEUG_RUN_MAIN'] = 'true'

        # a weird bug on windows. sometimes unicode strings end up in the
        # environment and subprocess.call does not like this, encode them
        # to latin1 and continue.
        if os.name == 'nt' and PY2:
            for key, value in iteritems(new_environ):
                if isinstance(value, text_type):
                    new_environ[key] = value.encode('iso-8859-1')

        exit_code = gevent.subprocess.call(args, env=new_environ)
        if exit_code != 3:
            return exit_code


def run_with_reloader(main_func, extra_files=None, interval=1):
    """Run the given function in an independent python interpreter."""
    import signal
    gevent.signal(signal.SIGTERM, lambda *args: sys.exit(0))
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        main_greenlet = gevent.spawn(main_func)
        try:
            _reloader_stat_loop(main_greenlet, extra_files, interval)
        except KeyboardInterrupt:
            return
    try:
        sys.exit(restart_with_reloader())
    except KeyboardInterrupt:
        pass
