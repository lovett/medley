"""
Test suite for the whois app
"""

import unittest
import mock
from testing.assertions import ResponseAssertions
from testing import helpers
from testing.cptestcase import BaseCherryPyTestCase
import apps.bounce.main


class TestBounce(BaseCherryPyTestCase, ResponseAssertions):
    """
    Tests for the bounce application controller
    """

    @classmethod
    def setUpClass(cls):
        """Start a faux cherrypy server"""
        helpers.start_server(apps.bounce.main.Controller)

    @classmethod
    def tearDownClass(cls):
        """Shut down the faux server"""
        helpers.stop_server()

    def setUp(self):
        """Provide a separate controller instance for testing helper methods.

        """

        self.controller = apps.bounce.main.Controller()

    def test_allow(self):
        """Verify the controller's supported HTTP methods"""

        response = self.request("/", method="HEAD")
        self.assertAllowedMethods(response, ("GET", "PUT"))

    def test_site_url(self):
        """An incoming URL is reduced to its protocol and hostname."""

        candidates = (
            ("https://example.com/with/a/path",
             "https://example.com"),
            ("http://example.com/path?and=querystring#andfragment",
             "http://example.com"),
        )

        for pair in candidates:
            result = self.controller.site_url(pair[0])
            self.assertEqual(result, pair[1])

    def test_guess_group(self):
        """URLs are grouped by subtracting known keywords from the
        hostname.

        """

        candidates = (
            ("http://example.com", "example"),
            ("http://dev.example.com", "example"),
            ("http://stage.example.com", "example"),
            ("http://staging.example.com", "example"),
            ("http://somethingelse.example.com", "example"),
            ("http://sub1.sub2.sub3.example.co.uk", "example"),
            ("http://example.local", "example"),
            ("http://example", "example"),
        )

        for pair in candidates:
            result = self.controller.guess_group(pair[0])
            self.assertEqual(result, pair[1])

    def test_guess_name(self):
        """URLs are named by looking for known keywords in the hostname."""

        candidates = (
            ("http://example.co.uk", "live"),
            ("http://dev.example.com", "dev"),
            ("http://stage.example.com", "stage"),
            ("http://staging.example.com", "staging"),
            ("http://somethingelse.example.com", "live"),
            ("http://sub1.sub2.sub3.example.co.uk", "live"),
            ("http://example.local", "local"),
            ("http://example", "dev"),
        )

        for pair in candidates:
            result = self.controller.guess_name(pair[0])
            self.assertEqual(result, pair[1])

    @mock.patch("cherrypy.tools.negotiable._renderHtml")
    @mock.patch("cherrypy.engine.publish")
    def test_site_in_group(self, publish_mock, render_mock):
        """A request with a URL that belongs to known group returns
        equivalent URLs for other members of the group
        """

        def side_effect(*args, **_):
            """Side effects local function"""

            if args[0] == "registry:first_key":
                return ["example"]

            if args[0] == "registry:search":
                return [[
                    {
                        "rowid": 1,
                        "key": "bounce:example",
                        "value": "http://stage.example.com\nstage",
                    },
                    {
                        "rowid": 2,
                        "key": "bounce:example",
                        "value": "http://othersite.example.com\nothersite"
                    }
                ]]

            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        self.request("/", u="http://dev.example.com/with/subpath")

        self.assertEqual(
            helpers.html_var(render_mock, "group"),
            "example"
        )

        self.assertIsNone(
            helpers.html_var(render_mock, "name")
        )

        bounce_var = helpers.html_var(render_mock, "bounces")

        self.assertEqual(
            bounce_var[1][0],
            "http://stage.example.com/with/subpath"
        )

        self.assertEqual(
            bounce_var[1][1],
            "stage"
        )

        self.assertEqual(
            bounce_var[2][0],
            "http://othersite.example.com/with/subpath"
        )

        self.assertEqual(
            bounce_var[2][1],
            "othersite"
        )

    @mock.patch("cherrypy.tools.negotiable._renderHtml")
    @mock.patch("cherrypy.engine.publish")
    def test_unrecognized_site(self, publish_mock, render_mock):
        """A  URL that does not belong to known group returns a form."""

        def side_effect(*args, **_):
            """Side effects local function"""

            if args[0] == "registry:first_key":
                return [None]

            if args[0] == "registry:search":
                return [None]

            if args[0] == "registry:distinct_keys":
                return [None]

            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        self.request("/", u="http://unrecognized.example.com")

        self.assertEqual(
            helpers.html_var(render_mock, "group"),
            "example"
        )

        self.assertEqual(
            helpers.html_var(render_mock, "name"),
            "live"
        )

        self.assertIsNone(
            helpers.html_var(render_mock, "bounces")
        )

        self.assertEqual(
            helpers.html_var(render_mock, "all_groups"),
            []
        )

    @mock.patch("cherrypy.tools.negotiable._renderHtml")
    @mock.patch("cherrypy.engine.publish")
    def test_bookmarklet_url_https(self, publish_mock, render_mock):
        """The bookmarklet URL respects HTTPS."""

        def side_effect(*args, **_):
            """Side effects local function"""
            if args[0] == "registry:first_key":
                return [None]

            if args[0] == "registry:search":
                return [None]

            if args[0] == "registry:distinct_keys":
                return [None]

            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        self.request(
            "/",
            headers={"X-HTTPS": "On"},
            u="http://unrecognized.example.com"
        )

        self.assertTrue(
            helpers.html_var(render_mock, "app_url").startswith("https")
        )

    @mock.patch("cherrypy.engine.publish")
    def test_add_site(self, publish_mock):
        """A new site can be added to a group"""

        def side_effect(*args, **_):
            """Side effects local function"""
            if args[0] == "registry:add":
                return [{"uid": 1, "group": "example"}]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        response = self.request(
            "/",
            method="PUT",
            site="http://dev.example.com",
            group="example",
            name="dev",
        )

        self.assertEqual(response.code, 204)


if __name__ == "__main__":
    unittest.main()
