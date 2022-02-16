"""Test suite for the whois app."""

from typing import Any
import unittest
from unittest import mock
from testing.assertions import ResponseAssertions
from testing import helpers
from testing.cptestcase import BaseCherryPyTestCase
import apps.bounce.main  # type: ignore


class TestBounce(BaseCherryPyTestCase, ResponseAssertions):
    """Tests for the application controller."""

    @classmethod
    def setUpClass(cls) -> None:
        """Start a faux cherrypy server"""
        helpers.start_server(apps.bounce.main.Controller)

    @classmethod
    def tearDownClass(cls) -> None:
        """Shut down the faux server"""
        helpers.stop_server()

    def setUp(self) -> None:
        """Use a separate controller instance for testing helper methods."""

        self.controller = apps.bounce.main.Controller()

    def test_allow(self) -> None:
        """Verify the controller's supported HTTP methods"""
        response = self.request("/", method="HEAD")
        self.assert_allowed(response, ("GET", "POST"))

    def test_exposed(self) -> None:
        """The application is publicly available."""
        self.assert_exposed(apps.bounce.main.Controller)

    def test_show_on_homepage(self) -> None:
        """The application is displayed in the bounce app."""
        self.assert_show_on_homepage(apps.bounce.main.Controller)

    def test_group_reduction(self) -> None:
        """URLs are associated with one another by subtracting known
        keywords from the hostname."""

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
            result = self.controller.url_to_group(pair[0])
            self.assertEqual(result, pair[1])

    def test_keyword_redution(self) -> None:
        """Site names are identified by isolating common words."""

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
            result = self.controller.url_to_name(pair[0])
            self.assertEqual(result, pair[1])

    @mock.patch("cherrypy.engine.publish")
    def test_site_in_group(self, publish_mock: mock.Mock) -> None:
        """A request with a URL that belongs to known group returns
        equivalent URLs for other members of the group
        """

        def side_effect(*args: str, **_: str) -> Any:
            """Side effects local function"""

            if args[0] == "registry:first:key":
                return ["http://example.com"]

            if args[0] == "registry:search":
                return [(3, (
                    {
                        "rowid": 1,
                        "key": "bounce:example:stage",
                        "value": "http://stage.example.com",
                    },
                    {
                        "rowid": 2,
                        "key": "bounce:example:othersite",
                        "value": "http://othersite.example.com"
                    },
                    {
                        "rowid": 3,
                        "key": "bounce:example:dev",
                        "value": "http://dev.example.com"
                    }
                ))]
            if args[0] == "jinja:render":
                return [""]

            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        self.request("/", u="http://dev.example.com/with/subpath")

        self.assertEqual(
            helpers.template_var(publish_mock, "group"),
            "example"
        )

        self.assertEqual(
            helpers.template_var(publish_mock, "name"),
            "dev",
        )

        bounces = helpers.template_var(publish_mock, "bounces")

        self.assertEqual(
            bounces[0].address,
            "http://stage.example.com/with/subpath"
        )

        self.assertEqual(
            bounces[0].text,
            "stage"
        )

        self.assertEqual(
            bounces[1].address,
            "http://othersite.example.com/with/subpath"
        )

        self.assertEqual(
            bounces[1].text,
            "othersite"
        )

    @mock.patch("cherrypy.engine.publish")
    def test_site_not_in_group(self, publish_mock: mock.Mock) -> None:
        """A request with a URL that belongs to known group but does not match
        an existing record does not offer a list of bounces.

        """

        def side_effect(*args: str, **_: str) -> Any:
            """Side effects local function"""

            if args[0] == "registry:first:key":
                return ["example"]

            if args[0] == "registry:search":
                return [(2, (
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
                ))]

            if args[0] == "jinja:render":
                return [""]

            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        self.request("/", u="http://dev.example.com/with/subpath")

        self.assertEqual(
            len(helpers.template_var(publish_mock, "bounces")),
            0
        )

    @mock.patch("cherrypy.engine.publish")
    def test_unrecognized_site(self, publish_mock: mock.Mock) -> None:
        """A  URL that does not belong to known group returns a form."""

        def side_effect(*args: str, **_: str) -> Any:
            """Side effects local function"""

            if args[0] == "registry:first:key":
                return [None]

            if args[0] == "registry:search":
                return [(0, None)]

            if args[0] == "jinja:render":
                return [""]

            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        self.request("/", u="http://unrecognized.example.com")

        self.assertEqual(
            helpers.template_var(publish_mock, "group"),
            "example"
        )

        self.assertEqual(
            helpers.template_var(publish_mock, "name"),
            "unrecognized"
        )

        self.assertEqual(
            len(helpers.template_var(publish_mock, "bounces")),
            0
        )

    @mock.patch("cherrypy.engine.publish")
    def test_bookmarklet_url_https(self, publish_mock: mock.Mock) -> None:
        """The bookmarklet URL respects HTTPS."""

        def side_effect(*args: str, **_: str) -> Any:
            """Side effects local function"""
            if args[0] == "registry:first:key":
                return [None]

            if args[0] == "registry:search":
                return [0, None]

            if args[0] == "jinja:render":
                return [""]

            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        self.request(
            "/",
            headers={"X-HTTPS": "On"},
            u="http://unrecognized.example.com"
        )

    @mock.patch("cherrypy.engine.publish")
    def test_departing_site(self, publish_mock: mock.Mock) -> None:
        """If the given URL matches a record in the registry, it is considered
         the departing site.

        """

        def side_effect(*args: str, **_: str) -> Any:
            """Side effects local function"""
            if args[0] == "registry:first:key":
                return ["http://example.com"]

            if args[0] == "registry:search":
                return [(2, (
                    {
                        "rowid": 1,
                        "key": "bounce:example:stage",
                        "value": "http://stage.example.com",
                    },
                    {
                        "rowid": 2,
                        "key": "bounce:example:othersite",
                        "value": "http://othersite.example.com"
                    }
                ))]

            if args[0] == "jinja:render":
                return [""]

            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        self.request(
            "/",
            u="http://othersite.example.com"
        )

        self.assertEqual(
            len(helpers.template_var(publish_mock, "bounces")),
            2
        )

    @mock.patch("cherrypy.engine.publish")
    def test_add_site(self, publish_mock: mock.Mock) -> None:
        """A new site can be added to a group"""

        def side_effect(*args: str, **_: str) -> Any:
            """Side effects local function."""
            if args[0] == "registry:replace":
                return [{"uid": 1, "group": "example"}]
            if args[0] == "app_url":
                return ["http://example.com"]
            if args[0] == "jinja:render":
                return [""]

            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        response = self.request(
            "/",
            method="POST",
            url="http://dev.example.com",
            group="example",
            name="dev",
        )

        self.assertEqual(response.code, 303)

    @mock.patch("cherrypy.engine.publish")
    def test_add_site_invalid_group(self, publish_mock: mock.Mock) -> None:
        """A POST is rejected if the provided group is non-alphanumeric."""

        def side_effect(*args: str, **_: str) -> Any:
            """Side effects local function."""
            if args[0] == "app_url":
                return ["http://example.com"]
            if args[0] == "jinja:render":
                return [""]

            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        response = self.request(
            "/",
            method="POST",
            url="http://dev.example.com",
            group="???",
            name="dev",
        )

        self.assertEqual(response.code, 303)

    @mock.patch("cherrypy.engine.publish")
    def test_add_site_invalid_name(self, publish_mock: mock.Mock) -> None:
        """A POST is rejected if the provided name is non-alphanumeric."""

        def side_effect(*args: str, **_: str) -> Any:
            """Side effects local function."""
            if args[0] == "app_url":
                return ["http://example.com"]
            if args[0] == "jinja:render":
                return [""]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        response = self.request(
            "/",
            method="POST",
            url="http://dev.example.com",
            group="example",
            name="???",
        )

        self.assertEqual(response.code, 303)


if __name__ == "__main__":
    unittest.main()
