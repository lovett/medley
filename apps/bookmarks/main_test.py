"""
Test suite for the bookmarks app.
"""

import unittest
import mock
from testing.assertions import ResponseAssertions
from testing import helpers
from testing.cptestcase import BaseCherryPyTestCase
import apps.bookmarks.main


class TestBookmarks(BaseCherryPyTestCase, ResponseAssertions):
    """
    Tests for the bookmarks application controller
    """

    @classmethod
    def setUpClass(cls):
        """Start a faux cherrypy server"""
        helpers.start_server(apps.bookmarks.main.Controller)

    @classmethod
    def tearDownClass(cls):
        """Shut down the faux server"""
        helpers.stop_server()

    def test_allow(self):
        """Verify the controller's supported HTTP methods"""
        response = self.request("/", method="HEAD")
        self.assert_allowed(response, ("GET", "POST", "DELETE"))

    def test_exposed(self):
        """The application is publicly available."""
        self.assert_exposed(apps.bookmarks.main.Controller)

    def test_user_facing(self):
        """The application is displayed in the homepage app."""
        self.assert_user_facing(apps.bookmarks.main.Controller)

    @mock.patch("cherrypy.tools.negotiable.render_html")
    @mock.patch("cherrypy.engine.publish")
    def test_empty(self, publish_mock, render_mock):
        """If the database is empty, a no-records message is returned"""

        def side_effect(*args, **_):
            """Side effects local function"""
            if args[0] == "bookmarks:recent":
                return [[[], 0, _]]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        self.request("/")

        self.assertEqual(
            len(helpers.html_var(render_mock, "bookmarks")),
            0
        )
        self.assertIsNone(helpers.html_var(render_mock, "query"))

    @mock.patch("cherrypy.engine.publish")
    def test_add_success(self, publish_mock):
        """A URL can be added to the database"""

        def side_effect(*args, **_):
            """Side effects local function"""
            if args[0] == "scheduler:add":
                return [True]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        response = self.request("/", url="http://example.com", method="POST")

        self.assertEqual(response.code, 204)

    @mock.patch("cherrypy.engine.publish")
    def test_add_fail(self, publish_mock):
        """URLs must be well-formed"""

        def side_effect(*args, **_):
            """Side effects local function"""
            if args[0] == "scheduler:add":
                return [False]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        response = self.request("/", url="not-a-url", method="POST")

        self.assertEqual(response.code, 400)

    @mock.patch("cherrypy.engine.publish")
    def test_delete_fail(self, publish_mock):
        """Deletion fails if the URL is not found"""

        def side_effect(*args, **_):
            """Side effects local function"""
            if args[0] == "bookmarks:remove":
                return [0]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        response = self.request("/", url="http://example.com", method="DELETE")
        self.assertEqual(response.code, 404)

    @mock.patch("cherrypy.engine.publish")
    def test_delete_success(self, publish_mock):
        """Successful deletion sends no response"""

        def side_effect(*args, **_):
            """Side effects local function"""
            if args[0] == "bookmarks:remove":
                return [1]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        response = self.request("/", url="http://example.com", method="DELETE")
        self.assertEqual(response.code, 204)


if __name__ == "__main__":
    unittest.main()
