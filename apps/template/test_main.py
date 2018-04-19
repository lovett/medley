"""
Test suite for the template app
"""

import unittest
import mock
from testing.assertions import ResponseAssertions
from testing import helpers
from testing.cptestcase import BaseCherryPyTestCase
import apps.template.main


class TestTemplate(BaseCherryPyTestCase, ResponseAssertions):
    """Unit tests for the template app"""

    @classmethod
    def setUpClass(cls):
        """Start a faux cherrypy server"""
        helpers.start_server(apps.template.main.Controller)

    @classmethod
    def tearDownClass(cls):
        """Shut down the faux server"""
        helpers.stop_server()

    def test_allow(self):
        """Verify the controller's supported HTTP methods"""
        response = self.request("/", method="HEAD")
        self.assertAllowedMethods(response, ("GET",))

    @mock.patch("cherrypy.engine.publish")
    def test_template(self, publish_mock):
        """Lorem ipsum dolor sit"""

        def side_effect(*args, **_):
            """Side effects local function"""
            if args[0] == "registry:search":
                return [None]
            if args[0] == "cache:get":
                return [None]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        self.request("/")

        self.assertTrue(1 > 0)


if __name__ == "__main__":
    unittest.main()
