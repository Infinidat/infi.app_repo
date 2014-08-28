from unittest import SkipTest
from .test_case import TestCase
from infi.app_repo.config import Configuration
from infi.app_repo import worker
from infi.execute import execute_async, execute_assert_success
from mock import patch
from os import path, remove, environ, listdir

class TasksTestCase(TestCase):
    def pull_file(self, config, basename, dirpath):
        from infi.app_repo import tasks
        dst = "data/incoming/" + basename
        if path.exists(dst):
            remove(dst)
        tasks.pull_package.run(config.remote.fqdn, config.base_directory,
                               '/'.join([dirpath, basename]))
        self.assertTrue(path.exists(dst))
        self.assertTrue(path.isfile(dst))

    def pull_msi(self, config):
        self.pull_file(config, "host-power-tools-1.10.1-windows-x86.msi", "/msi/x86")

    def pull_deb(self, config):
        self.pull_file(config, "host-power-tools-1.10.1-linux-ubuntu-natty-x86.deb",
                       "/deb/ubuntu/dists/natty/main/binary-i386")

    def pull_rpm(self, config):
        self.pull_file(config, "host-power-tools-1.10.1-linux-centos-6-x64.rpm",
                       "/rpm/centos/6/x86_64")

    def update_metadata(self, config):
        from infi.app_repo import tasks
        tasks.process_incoming.run(config.base_directory)

    def test_pull(self):
        if not environ.get("JENKINS_URL"):
            raise SkipTest("runs on our jenkins only")
        with self.with_new_devlopment_config_file() as configfile:
            cmd = "bin/app_repo -f {} install".format(configfile)
            execute_assert_success(cmd, shell=True)
            execute_assert_success("service app_repo_worker stop", shell=True)
            execute_assert_success("service app_repo_webserver stop", shell=True)
            config = Configuration.from_disk(configfile)
            worker.init(config)
            self.pull_msi(config)
            self.pull_deb(config)
            self.pull_rpm(config)
            before = listdir("data/incoming")
            self.update_metadata(config)
            after = listdir("data/incoming")
            self.assertNotEquals(before, after)

    def test_push(self):
        from os import path
        with self.with_new_devlopment_config_file() as configfile:
            config = Configuration.from_disk(configfile)
            worker.init(config)
            src = "incoming/host-power-tools-1.10.1-windows-x86.msi"
            with patch("infi.execute.execute_assert_success") as execute_assert_success:
                from infi.app_repo import tasks
                tasks.push_package.run(config.remote.fqdn, "user", "password", config.base_directory,
                                       src)
            self.assertTrue(execute_assert_success.called)
            execute_assert_success.assert_called_with(["curl", "-T", path.join(config.base_directory, src),
                                                       "ftp://user:password@repo.lab.il.infinidat.com"])
