"""
Test suite for the whois app
"""

import unittest
import mock
from testing.assertions import ResponseAssertions
from testing import helpers
from testing.cptestcase import BaseCherryPyTestCase
import apps.ip.main


class TestIp(BaseCherryPyTestCase, ResponseAssertions):
    """
    Tests for the application controller.
    """

    @classmethod
    def setUpClass(cls):
        helpers.start_server(apps.ip.main.Controller)

    @classmethod
    def tearDownClass(cls):
        helpers.stop_server()

    def test_allow(self):
        """Verify the controller's supported HTTP methods"""
        response = self.request("/", method="HEAD")
        self.assert_allowed(response, ("GET",))

    def test_exposed(self):
        """The application is publicly available."""
        self.assert_exposed(apps.ip.main.Controller)

    def test_show_on_homepage(self):
        """The application is displayed in the homepage app."""
        self.assert_show_on_homepage(apps.ip.main.Controller)

    @mock.patch("cherrypy.tools.negotiable.render_html")
    @mock.patch("cherrypy.engine.publish")
    def test_returns_html(self, publish_mock, render_mock):
        """GET returns text/html by default"""

        def side_effect(*args, **_):
            """Side effects local function"""

            if args[0] == "cache:get":
                return ["1.1.1.1"]

            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        self.request("/")

        self.assertEqual(
            helpers.html_var(render_mock, "external_ip"),
            "1.1.1.1"
        )
        self.assertEqual(
            helpers.html_var(render_mock, "client_ip"),
            "127.0.0.1"
        )

    @mock.patch("cherrypy.tools.negotiable.render_json")
    @mock.patch("cherrypy.engine.publish")
    def test_returns_json(self, publish_mock, render_mock):
        """GET returns application/json if requested"""

        def side_effect(*args, **_):
            """Side effects local function"""

            if args[0] == "cache:get":
                return ["1.1.1.1"]

            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        self.request("/", as_json=True)

        self.assertEqual(
            helpers.html_var(render_mock, "external_ip"),
            "1.1.1.1"
        )

    @mock.patch("cherrypy.tools.negotiable.render_text")
    @mock.patch("cherrypy.engine.publish")
    def test_returns_text(self, publish_mock, render_mock):
        """GET returns text/plain if requested"""

        def side_effect(*args, **_):
            """Side effects local function"""

            if args[0] == "cache:get":
                return ["1.1.1.1"]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        self.request("/", as_text=True)

        self.assertTrue("external_ip=1.1.1.1" in helpers.text_var(render_mock))

    @mock.patch("cherrypy.tools.negotiable.render_html")
    @mock.patch("cherrypy.engine.publish")
    def test_honors_xreal_ip(self, publish_mock, render_mock):
        """The X-Real-IP header takes precedence over Remote-Addr"""

        def side_effect(*args, **_):
            """Side effects local function"""

            if args[0] == "cache:get":
                return ["1.1.1.1"]

            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        self.request("/", headers={"X-Real-Ip": "2.2.2.2"})

        self.assertEqual(
            helpers.html_var(render_mock, "client_ip"),
            "2.2.2.2"
        )

    @mock.patch("cherrypy.engine.publish")
    def test_cache_save_on_success(self, publish_mock):
        """The external IP lookup is cached if successfully retrieved"""

        def side_effect(*args, **_):
            """Side effects local function"""

            if args[0] == "cache:get":
                return [None]
            if args[0] == "urlfetch:get":
                return ["3.3.3.3"]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        self.request("/", headers={"X-Real-Ip": "2.2.2.2"})

        publish_mock.assert_any_call(
            "cache:set",
            apps.ip.main.Controller.cache_key,
            "3.3.3.3",
            300
        )

    @mock.patch("cherrypy.engine.publish")
    def test_no_cache_save_on_fail(self, publish_mock):
        """The external IP lookup is not cached if retrieval fails"""

        def side_effect(*args, **_):
            """Side effects local function"""

            if args[0] in ("cache:get", "urlfetch:get"):
                return [None]

            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        self.request("/", headers={"X-Real-Ip": "2.2.2.2"})

        self.assertNotIn(
            "cache:set",
            (call[0] for call in publish_mock.call_args_list)
        )


if __name__ == "__main__":
    unittest.main()
