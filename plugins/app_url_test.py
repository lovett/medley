"""Test suite for the url plugin."""

import typing
import unittest
from unittest.mock import Mock, patch, DEFAULT
import cherrypy
from testing.assertions import Subscriber
import plugins.app_url


class TestUrl(Subscriber):
    """Tests for the url plugin."""

    def setUp(self) -> None:
        self.plugin = plugins.app_url.Plugin(cherrypy.engine)

    def tearDown(self) -> None:
        cherrypy.request.base = ""

    @patch("cherrypy.engine.subscribe")
    def test_subscribe(self, subscribe_mock: Mock) -> None:
        """Subscriptions are prefixed consistently."""

        self.plugin.start()
        self.assert_prefix(subscribe_mock, "app_url")

    def test_absolute_url(self) -> None:
        """A path-only URL is converted to an absolute URL with trailing
        slash.

        """

        cherrypy.request.base = "http://example.com"
        result = self.plugin.app_url("/hello/world")
        self.assertEqual(result, "http://example.com/hello/world/")

    def test_absolute_url_noslash(self) -> None:
        """A trailing slash is not added if the path looks like a file."""

        cherrypy.request.base = "http://example.com"
        result = self.plugin.app_url("my_file.js")
        self.assertEqual(result, "http://example.com/my_file.js")

    @patch("cherrypy.engine.publish")
    def test_config_fallback(self, publish_mock: Mock) -> None:
        """The base URL is taken from the registry."""

        def side_effect(*args: str, **_kwargs: str) -> typing.Any:
            """Side effects local function"""
            if args[0] == "registry:first:value":
                return ["http://example.com"]
            return DEFAULT

        publish_mock.side_effect = side_effect

        result = self.plugin.app_url("/a/b/c")
        self.assertEqual(result, "http://example.com/a/b/c/")

    def test_port_preserved(self) -> None:
        """A custom port is preserved if present."""

        cherrypy.request.base = "http://example.com:12345"
        result = self.plugin.app_url("/hello/world")
        self.assertEqual(result, "http://example.com:12345/hello/world/")

    @patch("cherrypy.engine.publish")
    def test_local_base(self, publish_mock: Mock) -> None:
        """A local base URL is ignored."""

        def side_effect(*args: str, **_kwargs: str) -> typing.Any:
            """Side effects local function"""
            if args[0] == "registry:first:value":
                return ["http://example.com"]
            return DEFAULT

        publish_mock.side_effect = side_effect

        cherrypy.request.base = "http://localhost/test"
        result = self.plugin.app_url("/local/url")
        self.assertEqual(result, "http://example.com/local/url/")

        cherrypy.request.base = "http://127.0.0.1/test"
        result = self.plugin.app_url("/local/url")
        self.assertEqual(result, "http://example.com/local/url/")

    def test_querystring(self) -> None:
        """Querystring parameters account for trailing slashes."""

        cherrypy.request.base = "http://example.com"

        # No querystring on path.
        result = self.plugin.app_url("/local/url", {
            "hello": "world"
        })

        self.assertEqual(
            result,
            "http://example.com/local/url/?hello=world"
        )

        # Appending to an existing querystring.
        result = self.plugin.app_url("/local/url/?foo=bar", {
            "hello2": "world2"
        })

        self.assertEqual(
            result,
            "http://example.com/local/url/?foo=bar&hello2=world2"
        )


if __name__ == "__main__":
    unittest.main()