"""Test suite for the input plugin."""

from typing import Any
import unittest
from unittest.mock import patch
from unittest import mock
import cherrypy
import plugins.input
from testing.assertions import Subscriber


class TestInput(Subscriber):
    """Tests for the input plugin."""

    def setUp(self) -> None:
        cherrypy.config["server_host"] = "example.com"
        cherrypy.config["server_port"] = 1234
        self.plugin = plugins.input.Plugin(cherrypy.engine)

    @patch("cherrypy.engine.subscribe")
    def test_subscribe(self, subscribe_mock: mock.Mock) -> None:
        """The plugin subscribes to registry changes."""

        self.plugin.start()
        self.assert_prefix(subscribe_mock, "registry")

    def test_placeholder(self) -> None:
        """Placeholder to force pytest to generate a coverage file."""
        pass   # pylint: disable=unnecessary-pass

    def test_unconfigured_keypress(self) -> None:
        """Keys with no configuration are ignored."""

        self.plugin.triggers = {}

        self.plugin.fire("KEY_X")

        self.assertTrue(True)

    @mock.patch("cherrypy.engine.publish")
    def test_configured_keypress(self, publish_mock: mock.Mock) -> None:
        """Keys with configuration trigger URL requests."""

        self.plugin.triggers = {
            "KEY_X": "POST /test\narg1=val1"
        }
        self.plugin.fire("KEY_X")

        publish_mock.assert_called_with(
            "urlfetch:post",
            "http://example.com:1234/test",
            data={"arg1": ["val1"]}
        )


if __name__ == "__main__":
    unittest.main()
