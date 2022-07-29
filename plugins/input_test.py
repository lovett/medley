"""Test suite for the input plugin."""

import unittest
from unittest.mock import patch
from unittest import mock
import cherrypy
import plugins.input
from testing.assertions import Subscriber


class TestInput(Subscriber):
    """Tests for the input plugin."""

    def setUp(self) -> None:
        self.plugin = plugins.input.Plugin(cherrypy.engine)

    @patch("cherrypy.engine.subscribe")
    def test_subscribe(self, subscribe_mock: mock.Mock) -> None:
        """The plugin subscribes to registry changes."""

        self.plugin.start()
        self.assert_prefix(subscribe_mock, "registry")

    def test_placeholder(self) -> None:
        """Placeholder to force pytest to generate a coverage file."""
        pass   # pylint: disable=unnecessary-pass


if __name__ == "__main__":
    unittest.main()
