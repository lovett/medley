"""Test suite for the speak app."""

from typing import Any
import unittest
from unittest import mock
from testing.assertions import ResponseAssertions
from testing import helpers
from testing.cptestcase import BaseCherryPyTestCase
import apps.speak.main  # type: ignore


class TestSpeak(BaseCherryPyTestCase, ResponseAssertions):
    """Tests for the application controller."""

    @classmethod
    def setUpClass(cls) -> None:
        """Start a faux cherrypy server"""
        helpers.start_server(apps.speak.main.Controller)

    @classmethod
    def tearDownClass(cls) -> None:
        """Shut down the faux server"""
        helpers.stop_server()

    def test_allow(self) -> None:
        """Verify the controller's supported HTTP methods"""
        response = self.request("/", method="HEAD")
        self.assert_allowed(response, ("GET", "HEAD", "POST"))

    def test_exposed(self) -> None:
        """The application is publicly available."""
        self.assert_exposed(apps.speak.main.Controller)

    def test_show_on_homepage(self) -> None:
        """The application is displayed in the homepage app."""
        self.assert_show_on_homepage(apps.speak.main.Controller)

    @mock.patch("cherrypy.engine.publish")
    def test_muted(self, publish_mock: mock.Mock) -> None:
        """If the application is muted, responses are returned with 202"""

        def side_effect(*args: str, **_: str) -> Any:
            """Side effects local function"""

            if args[0] == "speak:muted":
                return [True]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        response = self.request(
            "/",
            method="POST",
            statement="hello"
        )

        self.assertEqual(response.code, 202)

    @mock.patch("cherrypy.engine.publish")
    def test_not_muted(self, publish_mock: mock.Mock) -> None:
        """Valid notifications trigger a speak event"""

        def side_effect(*args: str, **_: str) -> Any:
            """Side effects local function"""

            if args[0] == "speak:muted":
                return [False]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        response = self.request(
            "/",
            method="POST",
            statement="hello not muted"
        )

        self.assertEqual(response.code, 204)

        self.assertEqual(
            publish_mock.call_args[0][1],
            "hello not muted"
        )


if __name__ == "__main__":
    unittest.main()
