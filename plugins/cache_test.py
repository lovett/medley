"""Test suite for the cache plugin."""

import unittest
from unittest.mock import Mock, patch
import cherrypy
import plugins.cache
from testing.assertions import Subscriber


class TestCache(Subscriber):
    """Tests for the cache plugin."""

    def setUp(self) -> None:
        self.plugin = plugins.cache.Plugin(cherrypy.engine)

    @patch("cherrypy.engine.subscribe")
    def test_subscribe(self, subscribe_mock: Mock) -> None:
        """Subscriptions are prefixed consistently."""

        self.plugin.start()
        self.assert_prefixes(subscribe_mock, ("server", "cache"))

    def test_placeholder(self) -> None:
        """Placeholder to force pytest to generate a coverage file."""
        pass   # pylint: disable=unnecessary-pass


if __name__ == "__main__":
    unittest.main()
