"""Test suite for the bookmarks app."""

from typing import Any
import unittest
from unittest import mock
from testing.assertions import ResponseAssertions
from testing import helpers
from testing.cptestcase import BaseCherryPyTestCase
import apps.bookmarks.main  # type: ignore


class TestBookmarks(BaseCherryPyTestCase, ResponseAssertions):
    """
    Tests for the application controller.
    """

    @classmethod
    def setUpClass(cls) -> None:
        """Start a faux cherrypy server"""
        helpers.start_server(apps.bookmarks.main.Controller)

    @classmethod
    def tearDownClass(cls) -> None:
        """Shut down the faux server"""
        helpers.stop_server()

    def test_allow(self) -> None:
        """Verify the controller's supported HTTP methods"""
        response = self.request("/", method="HEAD")
        self.assert_allowed(response, ("GET", "POST", "DELETE"))

    def test_exposed(self) -> None:
        """The application is publicly available."""
        self.assert_exposed(apps.bookmarks.main.Controller)

    def test_show_on_homepage(self) -> None:
        """The application is displayed in the homepage app."""
        self.assert_show_on_homepage(apps.bookmarks.main.Controller)

    @mock.patch("cherrypy.engine.publish")
    def test_empty(self, publish_mock: mock.Mock) -> None:
        """If the database is empty, a no-records message is returned"""

        def side_effect(*args: str, **_: str) -> Any:
            if args[0] == "bookmarks:recent":
                return [[[], 0, _]]
            if args[0] == "jinja:render":
                return [""]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        self.request("/")

        self.assertEqual(
            helpers.template_var(publish_mock, "bookmarks"),
            []
        )
        self.assertIsNone(
            helpers.template_var(publish_mock, "query")
        )

    @mock.patch("cherrypy.engine.publish")
    def test_add_success(self, publish_mock: mock.Mock) -> None:
        """A URL can be added to the database"""

        def side_effect(*args: str, **_: str) -> Any:
            if args[0] == "scheduler:add":
                return [True]
            if args[0] == "jinja:render":
                return [""]

            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        response = self.request("/", url="http://example.com", method="POST")

        self.assertEqual(response.code, 204)

    @mock.patch("cherrypy.engine.publish")
    def test_add_fail(self, publish_mock: mock.Mock) -> None:
        """URLs must be well-formed"""

        def side_effect(*args: str, **_: str) -> Any:
            if args[0] == "scheduler:add":
                return [False]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        response = self.request("/", url="not-a-url", method="POST")

        self.assertEqual(response.code, 400)

    @mock.patch("cherrypy.engine.publish")
    def test_delete_fail(self, publish_mock: mock.Mock) -> None:
        """Deletion fails if the URL is not found"""

        def side_effect(*args: str, **_: str) -> Any:
            if args[0] == "bookmarks:remove":
                return [0]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        response = self.request("/12345", method="DELETE")
        self.assert_status(response, 404)

    @mock.patch("cherrypy.engine.publish")
    def test_delete_success(self, publish_mock: mock.Mock) -> None:
        """Successful deletion sends no response"""

        def side_effect(*args: str, **_: str) -> Any:
            if args[0] == "bookmarks:remove":
                return [1]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        response = self.request("/123", method="DELETE")
        self.assert_status(response, 204)

    @mock.patch("cherrypy.engine.publish")
    def test_wayback(self, publish_mock: mock.Mock) -> None:
        """Wayback lookup requests accommodate json."""

        def side_effect(*args: str, **_: str) -> Any:
            if args[0] == "urlfetch:get:json":
                return [({}, None)]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        response = self.request(
            "/",
            accept="json",
            wayback="http://example.com"
        )
        self.assert_status(response, 200)


if __name__ == "__main__":
    unittest.main()
