from .test_case import TestCase
from infi.app_repo.config import Configuration
from infi.app_repo import worker
from mock import patch
from os import path, remove

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
        self.pull_file(config, "cygwin-deployment-0.4.1-develop-windows-x86.msi", "/msi/x86")

    def pull_deb(self, config):
        self.pull_file(config, "host-power-tools-0.12-develop-linux-ubuntu-natty-x86.deb",
                       "/deb/ubuntu/dists/natty/main/binary-i386")

    def pull_rpm(self, config):
        self.pull_file(config, "host-power-tools-0.12-develop-linux-centos-6-x64.rpm",
                       "/rpm/centos/6/x86_64")

    def update_metadata(self, config):
        from infi.app_repo import tasks
        tasks.process_incoming.run(config.base_directory)

    def test_pull(self):
        with self.with_new_devlopment_config_file() as configfile:
            config = Configuration.from_disk(configfile)
            worker.init(config)
            self.pull_msi(config)
            self.pull_deb(config)
            self.pull_rpm(config)
            self.update_metadata(config)

    def test_push(self):
        from os import path
        with self.with_new_devlopment_config_file() as configfile:
            config = Configuration.from_disk(configfile)
            worker.init(config)
            src = "incoming/cygwin-deployment-0.4.1-develop-windows-x86.msi"
            with patch("infi.execute.execute_assert_success") as execute_assert_success:
                from infi.app_repo import tasks
                tasks.push_package.run(config.remote.fqdn, "user", "password", config.base_directory,
                                       src)
            self.assertTrue(execute_assert_success.called)
            execute_assert_success.assert_called_with(["curl", "-T", path.join(config.base_directory, src),
                                                       "ftp://user:password@repo.lab.il.infinidat.com:"])
