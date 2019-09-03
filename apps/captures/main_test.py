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
        self.assert_allowed(response, ("GET",))

    @mock.patch("cherrypy.tools.negotiable.render_html")
    @mock.patch("cherrypy.engine.publish")
    def test_search_by_path(self, publish_mock, render_mock):
        """Captures can be searched by path"""

        def side_effect(*args, **_):
            """Side effects local function"""
            if args[0] == "capture:search":
                return [(1, [{}])]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        self.request("/", path="test")

        print(render_mock.call_args_list)

        self.assertEqual(len(helpers.html_var(render_mock, "captures")), 1)


if __name__ == "__main__":
    unittest.main()
