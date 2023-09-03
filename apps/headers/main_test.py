"""Test suite for the whois app."""

from typing import Any
import unittest
from unittest import mock
from testing.assertions import ResponseAssertions
from testing import helpers
from testing.cptestcase import BaseCherryPyTestCase
import apps.headers.main  # type: ignore


class TestHeaders(BaseCherryPyTestCase, ResponseAssertions):

    @classmethod
    def setUpClass(cls) -> None:
        """Start a faux cherrypy server"""
        helpers.start_server(apps.headers.main.Controller)

    @classmethod
    def tearDownClass(cls) -> None:
        """Shut down the faux server"""
        helpers.stop_server()

    def test_allow(self) -> None:
        """Verify the controller's supported HTTP methods"""
        response = self.request("/", method="HEAD")
        self.assert_allowed(response, ("GET",))

    def test_exposed(self) -> None:
        """The application is publicly available."""
        self.assert_exposed(apps.headers.main.Controller)

    def test_show_on_homepage(self) -> None:
        """The application is displayed in the homepage app."""
        self.assert_show_on_homepage(apps.headers.main.Controller)

    @mock.patch("cherrypy.engine.publish")
    def test_returns_html(self, publish_mock: mock.Mock) -> None:
        """GET returns text/html by default"""

        def side_effect(*args: str, **_: str) -> Any:
            if args[0] == "jinja:render":
                return [""]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        self.request("/", headers={
            "X-Test": "Hello"
        })

        self.assertIn(
            ("X-Test", "Hello"),
            helpers.template_var(publish_mock, "headers")
        )

    def test_returns_json(self) -> None:
        """GET returns application/json if requested"""
        response = self.request("/", accept="json")
        self.assertEqual(response.code, 200)
        self.assert_json(response)

    def test_returns_text(self) -> None:
        """GET returns text/plain if requested"""
        response = self.request("/", accept="text")
        self.assert_text(response)

    def test_custom_header(self) -> None:
        """GET recognizes custom headers"""

        response = self.request(
            "/",
            headers={"Special_Header": "Special Value"},
            accept="json"
        )

        pair = next(
            pair
            for pair in response.json
            if pair[0] == "Special_Header"
        )

        self.assertEqual(pair[1], "Special Value")


if __name__ == "__main__":
    unittest.main()
