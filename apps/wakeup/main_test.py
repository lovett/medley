"""Test suite for the wakeup app."""

import typing
import unittest
from unittest import mock
from testing.assertions import ResponseAssertions
from testing import helpers
from testing.cptestcase import BaseCherryPyTestCase
import apps.wakeup.main  # type: ignore


class TestWakeup(BaseCherryPyTestCase, ResponseAssertions):
    """
    Tests for the application controller.
    """

    @classmethod
    def setUpClass(cls) -> None:
        helpers.start_server(apps.wakeup.main.Controller)

    @classmethod
    def tearDownClass(cls) -> None:
        helpers.stop_server()

    def test_allow(self) -> None:
        """Verify the controller's supported HTTP methods"""
        response = self.request("/", method="HEAD")
        self.assert_allowed(response, ("GET", "POST"))

    def test_exposed(self) -> None:
        """The application is publicly available."""
        self.assert_exposed(apps.wakeup.main.Controller)

    def test_show_on_homepage(self) -> None:
        """The application is displayed in the homepage app."""
        self.assert_show_on_homepage(apps.wakeup.main.Controller)

    @mock.patch("cherrypy.engine.publish")
    def test_get(self, publish_mock: mock.Mock) -> None:
        """The default view is a list of wake-able hosts."""

        def side_effect(*args: str, **_: str) -> typing.Any:
            """Side effects local function"""
            if args[0] == "registry:search:dict":
                return [{"host1": "mac1", "host2": "mac2"}]

            if args[0] == "app_url":
                return ["/registry"]

            if args[0] == "jinja:render":
                return [""]

            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        self.request("/")

        self.assertEqual(
            helpers.template_var(publish_mock, "registry_url"),
            "/registry"
        )
        self.assertEqual(
            helpers.template_var(publish_mock, "hosts").get("host1"),
            "mac1"
        )

        self.assertNotIn(
            "host3",
            helpers.template_var(publish_mock, "hosts")
        )

        self.assertFalse(
            helpers.template_var(publish_mock, "send")
        )

    def test_post_rejects_missing_host(self) -> None:
        """A host must be specified on POST."""

        response = self.request("/", method="POST")
        self.assertEqual(response.code, 400)

    @mock.patch("cherrypy.engine.publish")
    def test_post_rejects_unknown_host(self, publish_mock: mock.Mock) -> None:
        """WOL packets are not sent if the host is unknown."""

        def side_effect(*args: str, **_: str) -> typing.Any:
            """Side effects local function"""
            if args[0] == "registry:first:value":
                return [None]
            if args[0] == "jinja:render":
                return [""]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        response = self.request("/", method="POST", host="host1")

        self.assertEqual(response.code, 400)

    @mock.patch("cherrypy.engine.publish")
    def test_post_accepts_known_host(self, publish_mock: mock.Mock) -> None:
        """WOL packets are sent if the host is known."""

        def side_effect(*args: str, **_: str) -> typing.Any:
            """Side effects local function"""
            if args[0] == "registry:first:value":
                return ["00:00:00:00:00"]
            if args[0] == "app_url":
                return ["/"]
            if args[0] == "jinja:render":
                return [""]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        response = self.request("/", method="POST", host="host1")

        self.assertEqual(response.code, 303)

    @mock.patch("cherrypy.engine.publish")
    def test_post_sends_text(self, publish_mock: mock.Mock) -> None:
        """A plain-text response is sent with a success message."""

        def side_effect(*args: str, **_: str) -> typing.Any:
            """Side effects local function"""
            if args[0] == "registry:first:value":
                return ["00:00:00:00:00"]
            if args[0] == "app_url":
                return ["/"]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        response = self.request(
            "/",
            method="POST",
            accept="text",
            host="host1"
        )

        self.assertEqual(response.code, 200)
        self.assertEqual(response.body, "WoL packet sent.")


if __name__ == "__main__":
    unittest.main()
