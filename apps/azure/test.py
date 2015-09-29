import cptestcase
import helpers
import unittest
import responses
import apps.azure.main
import mock

class TestTopics(cptestcase.BaseCherryPyTestCase):
    @classmethod
    def setUpClass(cls):
        helpers.start_server(apps.azure.main.Controller)

    @classmethod
    def tearDownClass(cls):
        helpers.stop_server()

    def test_returnsHtml(self):
        """It returns HTML"""
        pass


if __name__ == "__main__":
    unittest.main()
