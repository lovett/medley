"""Test suite for the ip app."""

# pylint: disable=import-error

from typing import Any
import unittest
from unittest import mock
from testing.assertions import ResponseAssertions
from testing import helpers  # pylint: disable=import-error
from testing.cptestcase import BaseCherryPyTestCase
import apps.ip.main


class TestIp(BaseCherryPyTestCase, ResponseAssertions):

    @classmethod
    def setUpClass(cls) -> None:
        """Start a faux cherrypy server"""
        helpers.start_server(apps.ip.main.Controller)

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
        self.assert_exposed(apps.ip.main.Controller)

    def test_show_on_homepage(self) -> None:
        """The application is displayed in the homepage app."""
        self.assert_show_on_homepage(apps.ip.main.Controller)

    @mock.patch("cherrypy.engine.publish")
    def test_returns_html(self, publish_mock: mock.Mock) -> None:
        """GET returns text/html by default"""

        def side_effect(*args: str, **_: str) -> Any:

            if args[0] == "urlfetch:get:json":
                return [({"ip": "1.1.1.1"}, None)]
            if args[0] == "jinja:render":
                return [""]

            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        self.request("/")

        self.assertEqual(
            helpers.template_var(publish_mock, "external_ip"),
            "1.1.1.1"
        )
        self.assertEqual(
            helpers.template_var(publish_mock, "client_ip"),
            "127.0.0.1"
        )

    @mock.patch("cherrypy.engine.publish")
    def test_returns_json(self, publish_mock: mock.Mock) -> None:
        """GET returns application/json if requested"""

        def side_effect(*args: str, **_: str) -> Any:

            if args[0] == "urlfetch:get:json":
                return [({"ip": "1.1.1.1"}, None)]

            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        response = self.request("/", accept="json")

        self.assert_json(response)

        self.assertEqual(
            response.json.get("external_ip", ""),
            "1.1.1.1"
        )

    @mock.patch("cherrypy.engine.publish")
    def test_returns_text(self, publish_mock: mock.Mock) -> None:
        """GET returns text/plain if requested"""

        def side_effect(*args: str, **_: str) -> Any:

            if args[0] == "urlfetch:get:json":
                return [({"ip": "1.1.1.1"}, None)]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        response = self.request("/", accept="text")
        self.assert_text(response)

    @mock.patch("cherrypy.engine.publish")
    def test_honors_xreal_ip(self, publish_mock: mock.Mock) -> None:
        """The X-Real-IP header takes precedence over Remote-Addr"""

        def side_effect(*args: str, **_: str) -> Any:

            if args[0] == "urlfetch:get:json":
                return [({"ip": "1.1.1.1"}, None)]
            if args[0] == "jinja:render":
                return [""]

            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        self.request("/", headers={"X-Real-Ip": "2.2.2.2"})

        self.assertEqual(
            helpers.template_var(publish_mock, "client_ip"),
            "2.2.2.2"
        )


if __name__ == "__main__":
    unittest.main()
