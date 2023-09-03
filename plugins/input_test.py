"""Test suite for the input plugin."""

import unittest
from unittest.mock import patch
from unittest import mock
import cherrypy
import plugins.input
from testing.assertions import Subscriber


class TestInput(Subscriber):

    def setUp(self) -> None:
        cherrypy.config["server_host"] = "example.com"
        cherrypy.config["server_port"] = 1234
        self.plugin = plugins.input.Plugin(cherrypy.engine)

    @patch("cherrypy.engine.subscribe")
    def test_subscribe(self, subscribe_mock: mock.Mock) -> None:
        """The plugin subscribes to registry changes."""

        self.plugin.start()
        self.assert_prefix(subscribe_mock, "registry")

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
