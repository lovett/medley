"""Test suite for the whois app."""

from collections import defaultdict
import unittest
import typing
from unittest import mock
from testing.assertions import ResponseAssertions
from testing import helpers
from testing.cptestcase import BaseCherryPyTestCase
import apps.whois.main


class TestWhois(BaseCherryPyTestCase, ResponseAssertions):
    """
    Tests for the application controller.
    """

    @classmethod
    def setUpClass(cls) -> None:
        """Start a faux cherrypy server"""
        helpers.start_server(apps.whois.main.Controller)

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
        self.assert_exposed(apps.whois.main.Controller)

    def test_show_on_homepage(self) -> None:
        """The application is displayed in the homepage app."""
        self.assert_show_on_homepage(apps.whois.main.Controller)

    @mock.patch("socket.gethostbyname_ex")
    @mock.patch("cherrypy.engine.publish")
    def test_invalid_address_hostname(
            self,
            publish_mock: mock.Mock,
            socket_mock: mock.Mock
    ) -> None:
        """Request lookup of an invalid hostname"""

        def side_effect(*args: str, **_: str) -> typing.Any:
            """Side effects local function"""

            if args[0] == "url:internal":
                return ["/"]
            return True

        publish_mock.side_effect = side_effect

        socket_mock.side_effect = OSError

        response = self.request("/", address="invalid")
        self.assertEqual(response.code, 303)

    @mock.patch("cherrypy.engine.publish")
    def test_valid_address_as_hostname(self, publish_mock: mock.Mock) -> None:
        """Request lookup of a valid hostname"""

        def side_effect(*args: str, **_: str) -> typing.Any:
            """Side effects local function"""
            if args[0] == "url:internal":
                return ["/"]
            if args[0] in ("ip:facts", "logindex:count_visit_days"):
                return [{}]
            if args[0] in ("cache:get", "urlfetch:get"):
                return [None]
            if args[0] == "ip:reverse":
                return [defaultdict()]
            if args[0] == "jinja:render":
                return [""]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        self.request("/", address="localhost")

        self.assertEqual(
            helpers.template_var(publish_mock, "ip_address"),
            "127.0.0.1"
        )

    @mock.patch("cherrypy.engine.publish")
    def xtest_invalid_address_as_ip(self, publish_mock: mock.Mock) -> None:
        """Request lookup of an invalid IP address"""

        def side_effect(*args: str, **_: str) -> typing.Any:
            """Side effects local function"""
            if args[0] == "url:internal":
                return ["/"]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        response = self.request("/", address="333.333.333.333")
        self.assertEqual(response.code, 303)

    @mock.patch("cherrypy.engine.publish")
    def xtest_address_as_ip(self, publish_mock: mock.Mock) -> None:
        """Request lookup of a cached IP address"""

        cache_fake = {"foo": "bar"}

        def side_effect(*args: str, **_: str) -> typing.Any:
            """Overrides to be returned by the mock"""
            if args[0] == "cache:get":
                return [cache_fake]
            if args[0] == "urlfetch:get":
                return [None]
            if args[0] == "jinja:render":
                return [""]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        self.request("/", address="127.0.0.1")

        self.assertEqual(
            helpers.template_var(publish_mock, "whois"),
            cache_fake
        )

        self.assertEqual(
            helpers.template_var(publish_mock, "ip_facts"),
            cache_fake
        )

    @mock.patch("cherrypy.engine.publish")
    def test_address_as_ip_nocache(self, publish_mock: mock.Mock) -> None:
        """Request lookup of an uncached IP address"""

        def side_effect(*args: str, **_: str) -> typing.Any:
            """Side effects local function"""
            if args[0] == "cache:get":
                return [None]
            if args[0] == "ip:facts":
                return [{"hello": "world"}]
            if args[0] == "urlfetch:get":
                return [{"foo": "bar"}]
            if args[0] == "jinja:render":
                return [""]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        self.request("/", address="127.0.0.1")

        self.assertEqual(
            helpers.template_var(publish_mock, "ip_facts"),
            {"hello": "world"}
        )


if __name__ == "__main__":
    unittest.main()
