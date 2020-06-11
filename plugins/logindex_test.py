"""Test suite for the logindex plugin."""

import unittest
from unittest.mock import Mock, patch
import cherrypy
import plugins.logindex
from testing.assertions import Subscriber


class TestLogindex(Subscriber):
    """Tests for the logindex plugin."""

    def setUp(self) -> None:
        self.plugin = plugins.logindex.Plugin(cherrypy.engine)

    @patch("cherrypy.engine.subscribe")
    def test_subscribe(self, subscribe_mock: Mock) -> None:
        """Subscriptions are prefixed consistently."""

        self.plugin.start()
        self.assert_prefixes(subscribe_mock, ("logindex", "server"))

    def test_placeholder(self) -> None:
        """Placeholder to force pytest to generate a coverage file."""
        pass   # pylint: disable=unnecessary-pass


if __name__ == "__main__":
    unittest.main()
