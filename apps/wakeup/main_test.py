"""
Test suite for the wakeup app
"""

import unittest
import mock
from testing.assertions import ResponseAssertions
from testing import helpers
from testing.cptestcase import BaseCherryPyTestCase
import apps.wakeup.main


class TestWakeup(BaseCherryPyTestCase, ResponseAssertions):
    """
    Tests for the application controller.
    """

    @classmethod
    def setUpClass(cls):
        helpers.start_server(apps.wakeup.main.Controller)

    @classmethod
    def tearDownClass(cls):
        helpers.stop_server()

    def test_allow(self):
        """Verify the controller's supported HTTP methods"""
        response = self.request("/", method="HEAD")
        self.assert_allowed(response, ("GET", "POST"))

    def test_exposed(self):
        """The application is publicly available."""
        self.assert_exposed(apps.wakeup.main.Controller)

    def test_user_facing(self):
        """The application is displayed in the homepage app."""
        self.assert_user_facing(apps.wakeup.main.Controller)

    @mock.patch("cherrypy.tools.negotiable.render_html")
    @mock.patch("cherrypy.engine.publish")
    def test_get(self, publish_mock, render_mock):
        """The default view is a list of wake-able hosts."""

        def side_effect(*args, **_):
            """Side effects local function"""
            if args[0] == "registry:search":
                return [{"host1": "mac1", "host2": "mac2"}]

            if args[0] == "url:internal":
                return ["/registry"]

            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        self.request("/")

        self.assertEqual(
            helpers.html_var(render_mock, "registry_url"),
            "/registry"
        )
        self.assertEqual(
            helpers.html_var(render_mock, "hosts").get("host1"),
            "mac1"
        )

        self.assertNotIn(
            "host3",
            helpers.html_var(render_mock, "hosts")
        )

        self.assertFalse(
            helpers.html_var(render_mock, "sent")
        )

    @mock.patch("cherrypy.engine.publish")
    def test_post_rejects_unknown_host(self, publish_mock):
        """WOL packets are not sent if the host is unknown."""

        def side_effect(*args, **_):
            """Side effects local function"""
            if args[0] == "registry:first_value":
                return [None]

            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        response = self.request("/", method="POST", host="host1")

        self.assertEqual(response.code, 400)

    @mock.patch("cherrypy.engine.publish")
    def test_post_accepts_known_host(self, publish_mock):
        """WOL packets are sent if the host is known."""

        def side_effect(*args, **_):
            """Side effects local function"""
            if args[0] == "registry:first_value":
                return ["00:00:00:00:00"]
            if args[0] == "url:internal":
                return ["/"]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        response = self.request("/", method="POST", host="host1")

        self.assertEqual(response.code, 303)

    @mock.patch("cherrypy.engine.publish")
    def test_post_sends_text(self, publish_mock):
        """A plain-text response is sent with a success message."""

        def side_effect(*args, **_):
            """Side effects local function"""
            if args[0] == "registry:first_value":
                return ["00:00:00:00:00"]
            if args[0] == "url:internal":
                return ["/"]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        response = self.request("/", method="POST", as_text=True, host="host1")

        self.assertEqual(response.code, 200)
        self.assertEqual(response.body, "WoL packet sent.")


if __name__ == "__main__":
    unittest.main()
