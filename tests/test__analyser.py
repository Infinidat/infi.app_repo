from infi import unittest
from os import path
from infi.app_repo.webserver.analyser import Analyser

TESTS_DIR = path.abspath(path.dirname(__file__))
EMPTY = path.join(TESTS_DIR, "empty_metadata.json")
RICH = path.join(TESTS_DIR, "rich_metadata.json")

def get_metadata(filepath):
    from cjson import decode
    with open(filepath) as fd:
        return decode(fd.read())

EMPTY_SUGGESTION = (set(), set(),)

class FakeAnalyser(Analyser):
    def __init__(self, source, destination, base_directory="/tmp/"):
        super(FakeAnalyser, self).__init__(destination, base_directory)
        self.source = source
        self.destination = destination

    def get_our_metadata(self):
        return get_metadata(self.source)

    def get_their_metadata(self):
        return get_metadata(self.destination)

class AnalyserTestCase(unittest.TestCase):
    def test__get_ignored_packages(self):
        analyser = FakeAnalyser(EMPTY, RICH)
        self.assertEquals(dict(push=list(), pull=list()), analyser.get_ignored_packages())

    def test__get_packages(self):
        analyser = FakeAnalyser(EMPTY, RICH)
        self.assertEquals(set(), analyser.get_our_packages())
        self.assertNotEquals(set(), analyser.get_their_metadata())

    def test__suggestions__empty_to_rich(self):
        analyser = FakeAnalyser(EMPTY, RICH)
        self.assertNotEquals(EMPTY_SUGGESTION, analyser.suggest_packages_to_pull())
        self.assertEquals(EMPTY_SUGGESTION, analyser.suggest_packages_to_push())

    def test__suggestions__rich_to_empty(self):
        analyser = FakeAnalyser(RICH, EMPTY)
        self.assertNotEquals(EMPTY_SUGGESTION, analyser.suggest_packages_to_push())
        self.assertEquals(EMPTY_SUGGESTION, analyser.suggest_packages_to_pull())
