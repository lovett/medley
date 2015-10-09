import cptestcase
import helpers
import unittest
import responses
import apps.logindex.main
import mock
import util.db

class TestTopics(cptestcase.BaseCherryPyTestCase):
    @classmethod
    def setUpClass(cls):
        helpers.start_server(apps.logindex.main.Controller)

    @classmethod
    def tearDownClass(cls):
        helpers.stop_server()

    @mock.patch("util.db.cacheGet")
    def test_returnsHtml(self, cacheGetMock):
        """It returns HTML"""
        pass


if __name__ == "__main__":
    unittest.main()
