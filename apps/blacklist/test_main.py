from testing import assertions
from testing import cptestcase
from testing import helpers
import apps.blacklist.main
import cherrypy
import datetime
import mock
import unittest

class TestTemplate(cptestcase.BaseCherryPyTestCase, assertions.ResponseAssertions):
    """Unit tests for the template app"""

    @classmethod
    def setUpClass(cls):
        helpers.start_server(apps.blacklist.main.Controller)

    @classmethod
    def tearDownClass(cls):
        helpers.stop_server()

    def test_allow(self):
        response = self.request("/", method="HEAD")
        self.assertAllowedMethods(response, ("PUT", "DELETE"))

    @mock.patch("cherrypy.engine.publish")
    def test_blacklist(self, publishMock):
        def side_effect(*args, **kwargs):
            if args[0] == "phone:sanitize":
                return [123]

        response = self.request("/", method="PUT", number="x123")

        self.assertEqual(response.code, 204)

    @mock.patch("cherrypy.engine.publish")
    def test_unblacklist(self, publishMock):
        def side_effect(*args, **kwargs):
            if args[0] == "phone:sanitize":
                return [9998887777]

        response = self.request("/", method="DELETE", number="9998887777")

        self.assertEqual(response.code, 204)

if __name__ == "__main__":
    unittest.main()
