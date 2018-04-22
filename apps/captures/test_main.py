"""
Test suite for the captures app
"""

import unittest
import mock
from testing.assertions import ResponseAssertions
from testing import helpers
from testing.cptestcase import BaseCherryPyTestCase
import apps.captures.main


class TestRegistry(BaseCherryPyTestCase, ResponseAssertions):
    """
    Tests for the captures application controller
    """

    @classmethod
    def setUpClass(cls):
        """Start a faux cherrypy server"""
        helpers.start_server(apps.captures.main.Controller)

    @classmethod
    def tearDownClass(cls):
        """Shut down the faux server"""
        helpers.stop_server()

    def test_allow(self):
        """Verify the controller's supported HTTP methods"""

        response = self.request("/", method="HEAD")
        self.assertAllowedMethods(response, ("GET",))

    @mock.patch("cherrypy.tools.negotiable._renderHtml")
    @mock.patch("cherrypy.engine.publish")
    def test_recent(self, publish_mock, render_mock):
        """The default view is a list of recent captures"""

        def side_effect(*args, **_):
            """Side effects local function"""
            if args[0] == "capture:recent":
                return [[{}, {}, {}]]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        self.request("/")

        self.assertEqual(len(helpers.html_var(render_mock, "captures")), 3)

    @mock.patch("cherrypy.tools.negotiable._renderHtml")
    @mock.patch("cherrypy.engine.publish")
    def test_search(self, publish_mock, render_mock):
        """Captures can be searched"""

        def side_effect(*args, **_):
            """Side effects local function"""
            if args[0] == "capture:search":
                return [[{}]]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        self.request("/", query="test")

        self.assertEqual(len(helpers.html_var(render_mock, "captures")), 1)


if __name__ == "__main__":
    unittest.main()
