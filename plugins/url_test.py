"""Test suite for the url plugin."""

import typing
import unittest
from unittest.mock import Mock, patch, DEFAULT
import cherrypy
from testing.assertions import Subscriber
import plugins.url


class TestUrl(Subscriber):
    """Tests for the url plugin."""

    def setUp(self) -> None:
        self.plugin = plugins.url.Plugin(cherrypy.engine)

    @patch("cherrypy.engine.subscribe")
    def test_subscribe(self, subscribe_mock: Mock) -> None:
        """Subscriptions are prefixed consistently."""

        self.plugin.start()
        self.assert_prefix(subscribe_mock, "url")

    @patch("cherrypy.engine.publish")
    def test_absolute_url(self, publish_mock: Mock) -> None:
        """A path-only URL is converted to an absolute URL"""

        def side_effect(*args: str, **_kwargs: str) -> typing.Any:
            """Side effects local function"""
            if args[0] == "registry:first:value":
                return ["http://example.com"]
            return DEFAULT

        publish_mock.side_effect = side_effect

        result = self.plugin.internal_url("/hello/world")
        self.assertEqual(result, "http://example.com/hello/world")

    @patch("cherrypy.engine.publish")
    def test_port_preserved(self, publish_mock: Mock) -> None:
        """A base URL's custom port is preserved."""

        def side_effect(*args: str, **_kwargs: str) -> typing.Any:
            """Side effects local function"""
            if args[0] == "registry:first:value":
                return ["http://example.com:12345"]
            return DEFAULT

        publish_mock.side_effect = side_effect

        result = self.plugin.internal_url("/hello/world")
        self.assertEqual(result, "http://example.com:12345/hello/world")

    @patch("cherrypy.engine.publish")
    def test_no_local_url(self, publish_mock: Mock) -> None:
        """A local base URL is ignored."""

        def side_effect(*args: str, **_kwargs: str) -> typing.Any:
            """Side effects local function"""
            if args[0] == "registry:first:value":
                return ["http://example.com"]
            return DEFAULT

        publish_mock.side_effect = side_effect

        cherrypy.request.base = "http://127.0.0.1/test"
        result = self.plugin.internal_url("/local/url")
        self.assertEqual(result, "http://example.com/local/url")


if __name__ == "__main__":
    unittest.main()
