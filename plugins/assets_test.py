"""Test suite for the assets plugin."""

import unittest
from unittest.mock import Mock, patch
import cherrypy
import plugins.assets
from testing.assertions import Subscriber


class TestAssets(Subscriber):
    """Tests for the assets plugin."""

    def setUp(self) -> None:
        self.plugin = plugins.assets.Plugin(cherrypy.engine)

    @patch("cherrypy.engine.subscribe")
    def test_subscribe(self, subscribe_mock: Mock) -> None:
        """Subscriptions are prefixed consistently."""

        self.plugin.start()
        self.assert_prefix(subscribe_mock, "assets")

    def test_placeholder(self) -> None:
        """Placeholder to force pytest to generate a coverage file."""
        pass   # pylint: disable=unnecessary-pass


if __name__ == "__main__":
    unittest.main()
