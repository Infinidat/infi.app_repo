from .test_case import TestCase
from urllib2 import urlopen

class WebserverTestCase(TestCase):
    def test_home(self):
        with self.with_webserver_running():
            content = urlopen("http://localhost:8080").read()
            self.assertIn("Available packages", content)
