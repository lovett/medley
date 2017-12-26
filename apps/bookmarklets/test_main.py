from testing import assertions
from testing import cptestcase
from testing import helpers
import apps.bookmarklets.main
import cherrypy
import datetime
import mock
import unittest

class TestBookmarklets(cptestcase.BaseCherryPyTestCase, assertions.ResponseAssertions):
    """Unit tests for the bookmarklets app"""

    @classmethod
    def setUpClass(cls):
        helpers.start_server(apps.bookmarklets.main.Controller)

    @classmethod
    def tearDownClass(cls):
        helpers.stop_server()

    def extract_template_vars(self, mock):
        return mock.call_args[0][0]["html"][1]

    def test_allow(self):
        response = self.request("/", method="HEAD")
        self.assertAllowedMethods(response, ("GET",))

if __name__ == "__main__":
    unittest.main()
