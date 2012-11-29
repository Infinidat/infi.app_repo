from infi import unittest
from infi.pyutils.contexts import contextmanager
from infi.execute import execute_async, execute_assert_success
from time import sleep
from waiting import wait

@contextmanager
def with_tempfile():
    from tempfile import mkstemp
    from os import close, remove
    fd, path = mkstemp()
    close(fd)
    try:
        yield path
    finally:
        remove(path)

class TestCase(unittest.TestCase):
    @contextmanager
    def with_new_devlopment_config_file(self):
        with with_tempfile() as tempfile:
            cmd = "bin/app_repo dump defaults --development > {}".format(tempfile)
            execute_assert_success(cmd, shell=True)
            cmd = "bin/app_repo -f {} remote set repo.lab.il.infinidat.com beats me".format(tempfile)
            execute_assert_success(cmd, shell=True)
            yield tempfile

    @contextmanager
    def with_webserver_running(self, configfile=None):
        tempfile_context = self.with_new_devlopment_config_file()
        if configfile is None:
            configfile = tempfile_context.__enter__()
            self.addCleanup(tempfile_context.__exit__, None, None, None)
        pid = execute_async(["bin/app_repo", "-f", configfile, "webserver", "start"])
        sleep(2)
        try:
            # wait(lambda: 'Bus STARTED' in pid.get_stderr(), timeout_seconds=3)
            yield
        finally:
            pid.kill(9)
