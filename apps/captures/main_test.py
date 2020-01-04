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
    Tests for the application controller.
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

    def test_exposed(self):
        """The application is publicly available."""
        self.assert_exposed(apps.captures.main.Controller)

    def test_show_on_homepage(self):
        """The application is displayed in the homepage app."""
        self.assert_show_on_homepage(apps.captures.main.Controller)

    @mock.patch("cherrypy.engine.publish")
    def test_search_by_path(self, publish_mock):
        """Captures can be searched by path"""

        def side_effect(*args, **_):
            """Side effects local function"""
            if args[0] == "capture:search":
                return [(1, [{}])]
            if args[0] == "url:paginate:newer_older":
                return [(None, None)]
            if args[0] == "jinja:render":
                return [""]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        self.request("/", path="test")

        self.assertEqual(
            len(publish_mock.call_args_list[-1].kwargs.get("captures")),
            1
        )

    @mock.patch("cherrypy.engine.publish")
    def test_view_single_capture(self, publish_mock):
        """A single capture can be viewed by its ID."""

        def side_effect(*args, **_):
            """Side effects local function"""

            if args[0] == "capture:get":
                return [None]
            if args[0] == "jinja:render":
                return [""]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        self.request("/", cid="1")

        self.assertIsNone(
            publish_mock.call_args_list[-1].kwargs.get("newer_url"),
        )

        self.assertIsNone(
            publish_mock.call_args_list[-1].kwargs.get("older_url"),
        )


if __name__ == "__main__":
    unittest.main()
