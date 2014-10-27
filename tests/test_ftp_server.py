from .test_case import TemporaryBaseDirectoryTestCase
from infi.app_repo.config import Configuration
from infi.app_repo import ftpserver
from infi.app_repo.utils import ensure_directory_exists, path
from mock import patch
from munch import Munch
from StringIO import StringIO
from infi.pyutils.contexts import contextmanager


class FtpServerTestCase(TemporaryBaseDirectoryTestCase):
    def setUp(self):
        super(FtpServerTestCase, self).setUp()
        self.config = Configuration.from_disk(None)
        ensure_directory_exists(self.config.incoming_directory)
        self.test_succeded = False

    def mark_success(self, filepath):
        self.test_succeded = True

    @contextmanager
    def ftp_client_context(self, login=False):
        from ftplib import FTP
        client = FTP()
        client.connect('127.0.0.1', self.config.ftpserver.port)
        if login:
            client.login(self.config.ftpserver.username, self.config.ftpserver.password)
        self.addCleanup(client.close)
        try:
            yield client
        finally:
            client.close()

    @contextmanager
    def ftp_server_context(self):
        from threading import Thread
        server = ftpserver.start(self.config)
        serving_thread = Thread(target=server.serve_forever)
        serving_thread.start()
        try:
            yield server
        finally:
            server.close_all()
            serving_thread.join()

    def test_upload(self):
        with patch.object(ftpserver.AppRepoFtpHandler, "on_file_received") as on_file_received:
            on_file_received.side_effect = self.mark_success
            fd = StringIO("hello world")
            with self.ftp_server_context(), self.ftp_client_context(True) as client:
                client.storbinary("STOR testfile", fd)

        self.assertTrue(self.test_succeded)
        self.assertTrue(path.exists(path.join(self.config.incoming_directory, 'testfile')))

    def test_download(self):
        raise NotImplementedError()
