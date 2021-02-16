"""Test suite for the metrics plugin."""

import unittest
from unittest.mock import Mock, patch
import cherrypy
import plugins.metrics
from testing.assertions import Subscriber


class TestMetrics(Subscriber):
    """Tests for the metrics plugin."""

    def setUp(self) -> None:
        self.plugin = plugins.metrics.Plugin(cherrypy.engine)

    @patch("cherrypy.engine.subscribe")
    def test_subscribe(self, subscribe_mock: Mock) -> None:
        """Subscriptions are prefixed consistently."""

        self.plugin.start()
        self.assert_prefixes(subscribe_mock, ("server", "metrics"))

    def test_placeholder(self) -> None:
        """Placeholder to force pytest to generate a coverage file."""
        pass   # pylint: disable=unnecessary-pass


if __name__ == "__main__":
    unittest.main()
