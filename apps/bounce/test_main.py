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
        """Use a separate controller instance for testing helper methods."""

        self.controller = apps.bounce.main.Controller()

    def test_allow(self):
        """Verify the controller's supported HTTP methods"""

        response = self.request("/", method="HEAD")
        self.assertAllowedMethods(response, ("GET", "PUT", "DELETE"))

    def test_host_reduction(self):
        """An incoming URL is reduced to its host name."""

        candidates = (
            # Path is ignored.
            ("https://example.com/with/a/path",
             "example.com"),

            # Querystring and fragment are ignored.
            ("http://example.com/path?and=querystring#andfragment",
             "example.com"),

            # Scheme is ignored.
            ("https://example.com",
             "example.com"),

            # Port is preserved
            ("http://example.com:12345",
             "example.com:12345"),

            # Subdomains are preserved
            ("http://a.b.c.example.com",
             "a.b.c.example.com"),

            # Bare hostname is left intact
            ("site1.example.com", "site1.example.com")
        )

        for pair in candidates:
            result = self.controller.url_to_host(pair[0])
            self.assertEqual(result, pair[1])

    def test_group_reduction(self):
        """Hostnames are associated with one another by subtracting known
        keywords from the hostname.

        """

        candidates = (
            ("example.com", "example"),
            ("dev.example.com", "example"),
            ("stage.example.com", "example"),
            ("staging.example.com", "example"),
            ("somethingelse.example.com", "example"),
            ("sub1.sub2.sub3.example.co.uk", "example"),
            ("example.local", "example"),
            ("example", "example"),
            ("example.dev.something.invalid:12345", "example"),
        )

        for pair in candidates:
            result = self.controller.host_to_group(pair[0])
            self.assertEqual(result, pair[1])

    def test_keyword_redution(self):
        """Site environment keywords are identified by isolating common names.

        """

        candidates = (
            ("example.com", "live"),
            ("dev.example.com", "dev"),
            ("stage.example.com", "stage"),
            ("staging.example.com", "staging"),
            ("somethingelse.example.com", "somethingelse"),
            ("sub1.sub2.sub3.example.co.uk", "sub1"),
            ("example.local", "local"),
            ("example", "live"),
            ("example.dev.something.invalid:12345", "dev"),
        )

        for pair in candidates:
            result = self.controller.host_to_keyword(pair[0])
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
                        "key": "bounce:example:stage",
                        "value": "stage.example.com",
                    },
                    {
                        "rowid": 2,
                        "key": "bounce:example:othersite",
                        "value": "othersite.example.com"
                    },
                    {
                        "rowid": 3,
                        "key": "bounce:example:dev",
                        "value": "dev.example.com"
                    }

                ]]

            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        self.request("/", u="http://dev.example.com/with/subpath")

        self.assertEqual(
            helpers.html_var(render_mock, "group"),
            "example"
        )

        self.assertEqual(
            "dev",
            helpers.html_var(render_mock, "name")
        )

        bounces = helpers.html_var(render_mock, "bounces")

        self.assertEqual(
            bounces[1][0],
            "http://stage.example.com/with/subpath"
        )

        self.assertEqual(
            bounces[1][1],
            "stage"
        )

        self.assertEqual(
            bounces[2][0],
            "http://othersite.example.com/with/subpath"
        )

        self.assertEqual(
            bounces[2][1],
            "othersite"
        )

    @mock.patch("cherrypy.tools.negotiable._renderHtml")
    @mock.patch("cherrypy.engine.publish")
    def test_site_not_in_group(self, publish_mock, render_mock):
        """A request with a URL that belongs to known group but does not match
        an existing record does not offer a list of bounces.

        """

        def side_effect(*args, **_):
            """Side effects local function"""

            if args[0] == "registry:first_key":
                return ["example"]

            if args[0] == "registry:search":
                return [[
                    {
                        "rowid": 1,
                        "key": "bounce:example:stage",
                        "value": "stage.example.com",
                    },
                    {
                        "rowid": 2,
                        "key": "bounce:example:othersite",
                        "value": "othersite.example.com"
                    }
                ]]

            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        self.request("/", u="http://dev.example.com/with/subpath")

        bounces = helpers.html_var(render_mock, "bounces")

        self.assertEqual(len(bounces), 0)

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

            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        self.request("/", u="http://unrecognized.example.com")

        self.assertEqual(
            helpers.html_var(render_mock, "group"),
            "example"
        )

        self.assertEqual(
            helpers.html_var(render_mock, "name"),
            "unrecognized"
        )

        self.assertIsNone(
            helpers.html_var(render_mock, "bounces")
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

    @mock.patch("cherrypy.tools.negotiable._renderHtml")
    @mock.patch("cherrypy.engine.publish")
    def test_departing_site(self, publish_mock, render_mock):
        """If the given URL matches a record in the registry, it is considered
         the departing site.

        """

        def side_effect(*args, **_):
            """Side effects local function"""
            if args[0] == "registry:first_key":
                return ["example"]

            if args[0] == "registry:search":
                return [[
                    {
                        "rowid": 1,
                        "key": "bounce:example:stage",
                        "value": "stage.example.com",
                    },
                    {
                        "rowid": 2,
                        "key": "bounce:example:othersite",
                        "value": "othersite.example.com"
                    }
                ]]

            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        self.request(
            "/",
            u="http://othersite.example.com"
        )

        self.assertEqual(
            helpers.html_var(render_mock, "departing_from"),
            "othersite"
        )

    @mock.patch("cherrypy.engine.publish")
    def test_add_site(self, publish_mock):
        """A new site can be added to a group"""

        def side_effect(*args, **_):
            """Side effects local function."""
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

    @mock.patch("cherrypy.engine.publish")
    def test_delete_site(self, publish_mock):
        """A new site can be added to a group"""

        def side_effect(*args, **_):
            """Side effects local function."""
            if args[0] == "registry:remove_id":
                return [True]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        response = self.request(
            "/",
            method="DELETE",
            uid="1"
        )

        self.assertEqual(response.code, 204)


if __name__ == "__main__":
    unittest.main()
