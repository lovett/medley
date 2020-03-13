"""Test suite for the notification app."""

import typing
import unittest
import mock
from testing.assertions import ResponseAssertions
from testing import helpers
from testing.cptestcase import BaseCherryPyTestCase
import apps.notification.main


class TestHeaders(BaseCherryPyTestCase, ResponseAssertions):
    """
    Tests for the application controller.
    """

    @classmethod
    def setUpClass(cls) -> None:
        """Start a faux cherrypy server"""
        helpers.start_server(apps.notification.main.Controller)

    @classmethod
    def tearDownClass(cls) -> None:
        """Shut down the faux server"""
        helpers.stop_server()

    def test_allow(self) -> None:
        """Only POST requests are allowed"""
        response = self.request("/", method="HEAD")
        self.assert_allowed(response, ("POST",))

    def test_exposed(self) -> None:
        """The application is publicly available."""
        self.assert_exposed(apps.notification.main.Controller)

    def test_not_show_on_homepage(self) -> None:
        """The application is not displayed in the homepage app."""
        self.assert_not_show_on_homepage(apps.notification.main.Controller)

    def test_requires_json(self) -> None:
        """Request bodies must be JSON"""
        response = self.request("/", method="POST", hello="world")
        self.assertEqual(response.code, 415)

    def test_retraction(self) -> None:
        """Retractions are ignored"""
        fixture = {
            "retracted": [
                "123-456-789"
            ]
        }

        response = self.request(
            "/",
            method="POST",
            json_body=fixture
        )

        self.assertEqual(response.code, 202)

    @mock.patch("cherrypy.engine.publish")
    def test_skip(self, publish_mock: mock.Mock) -> None:
        """Reminders in skipped groups are ignored"""

        fixture = {
            "group": "reminder",
        }

        def side_effect(*args: str, **_: str) -> typing.Any:
            """Side effects local function"""
            if args[0] == "registry:search:valuelist":
                return ["reminder"]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        response = self.request(
            "/",
            method="POST",
            json_body=fixture
        )

        self.assertEqual(response.code, 202)

    @mock.patch("cherrypy.engine.publish")
    def test_no_title(self, publish_mock: mock.Mock) -> None:
        """Notifications without a title are ignored"""
        fixture = {
            "group": "test",
        }

        def side_effect(*args: str, **_: str) -> typing.Any:
            """Side effects local function"""
            if args[0] == "registry:search:valuelist":
                return [[]]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        response = self.request(
            "/",
            method="POST",
            json_body=fixture
        )

        self.assertEqual(response.code, 400)

    @mock.patch("cherrypy.engine.publish")
    def test_muted(self, publish_mock: mock.Mock) -> None:
        """If the application is muted, responses are returned with 202"""

        fixture = {
            "group": "test",
            "title": "hello world",
        }

        def side_effect(*args: str, **_: str) -> typing.Any:
            """Side effects local function"""
            if args[0] == "speak:muted":
                return [True]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        response = self.request(
            "/",
            method="POST",
            json_body=fixture,
        )

        self.assertEqual(response.code, 202)

    @mock.patch("cherrypy.engine.publish")
    def test_not_muted(self, publish_mock: mock.Mock) -> None:
        """Valid notifications trigger a speak event"""

        fixture = {
            "group": "test",
            "title": "hello world",
        }

        def side_effect(*args: str, **_: str) -> typing.Any:
            """Side effects local function"""
            if args[0] == "speak:muted":
                return [False]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        response = self.request(
            "/",
            method="POST",
            json_body=fixture,
        )

        self.assertEqual(response.code, 204)

        self.assertEqual(publish_mock.call_args[0][1], "hello world")


if __name__ == "__main__":
    unittest.main()
