from .test_case import TestCase
from infi.app_repo.config import Configuration
from infi.app_repo import worker
from mock import patch

class TasksTestCase(TestCase):
    def test_pull(self):
        with self.with_new_devlopment_config_file() as configfile:
            config = Configuration.from_disk(configfile)
            worker.init(config)
            from infi.app_repo import tasks
            from os import path, remove
            dst = "data/incoming/cygwin-deployment-0.4.1-develop-windows-x86.msi"
            if path.exists(dst):
                remove(dst)
            tasks.pull_package.run(config.remote.fqdn, config.base_directory,
                                   "/msi/x86/cygwin-deployment-0.4.1-develop-windows-x86.msi")
            self.assertTrue(path.exists(dst))
            self.assertTrue(path.isfile(dst))

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
