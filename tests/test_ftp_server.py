from .test_case import TemporaryBaseDirectoryTestCase
from infi.app_repo.config import Configuration
from infi.app_repo import ftpserver
from infi.app_repo.utils import ensure_directory_exists, path
from mock import patch
from StringIO import StringIO


class FtpServerTestCase(TemporaryBaseDirectoryTestCase):
    def setUp(self):
        super(FtpServerTestCase, self).setUp()
        self.config = Configuration.from_disk(None)
        ensure_directory_exists(self.config.incoming_directory)
        self.test_succeded = False

    def mark_success(self, filepath):
        self.test_succeded = True

    def test_upload(self):
        with patch.object(ftpserver.AppRepoFtpHandler, "on_file_received") as on_file_received:
            on_file_received.side_effect = self.mark_success
            fd = StringIO("hello world")
            with self.ftp_server_context(), self.ftp_client_context(True) as client:
                client.storbinary("STOR testfile", fd)

        self.assertTrue(self.test_succeded)
        self.assertTrue(path.exists(path.join(self.config.incoming_directory, 'testfile')))

    def test_download(self):
        with open(path.join(self.config.incoming_directory, 'testfile'), 'w') as fd:
            fd.write('hello world')

        with patch.object(ftpserver.AppRepoFtpHandler, "on_file_sent") as on_file_sent:
            on_file_sent.side_effect = self.mark_success

            with self.ftp_server_context(), self.ftp_client_context() as client:
                client.retrbinary('RETR incoming/testfile', lambda *args, **kwargs: None)

        self.assertTrue(self.test_succeded)



class FtpWithRpcTestCase(TemporaryBaseDirectoryTestCase):
    def setUp(self):
        from gevent.event import Event
        super(FtpWithRpcTestCase, self).setUp()
        self.config = Configuration.from_disk(None)
        ensure_directory_exists(self.config.incoming_directory)
        self.test_succeded = Event()

    def mark_success(self, filepath):
        self.test_succeded.set()

    def test_upload(self):
        from infi.app_repo import service
        with patch.object(service.AppRepoService, "_try_except_finally_process_source") as _try_except_finally_process_source:
            _try_except_finally_process_source.side_effect = self.mark_success
            fd = StringIO("hello world")
            with self.ftp_server_context(), self.ftp_client_context(True) as client:
                with self.rpc_server_context() as server:
                    client.storbinary("STOR testfile", fd)
                    self.test_succeded.wait(1)
        self.assertTrue(self.test_succeded.is_set())

    def test_upload_2(self):
        from infi.app_repo import service
        with patch.object(service.AppRepoService, "_try_except_finally_process_source") as _try_except_finally_process_source:
            _try_except_finally_process_source.side_effect = self.mark_success
            fd = StringIO("hello world")
            with self.rpc_server_context() as server:
                with self.ftp_server_context(), self.ftp_client_context(True) as client:
                    client.storbinary("STOR testfile", fd)
        self.assertTrue(self.test_succeded.is_set())
