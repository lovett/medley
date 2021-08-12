"""Test suite for the weather plugin."""

import unittest
from unittest.mock import Mock, patch
import cherrypy
import plugins.weather
from testing.assertions import Subscriber


class TestWeather(Subscriber):
    """Tests for the weather plugin."""

    def setUp(self) -> None:
        self.plugin = plugins.weather.Plugin(cherrypy.engine)

    @patch("cherrypy.engine.subscribe")
    def test_subscribe(self, subscribe_mock: Mock) -> None:
        """Subscriptions are prefixed consistently."""

        self.plugin.start()
        self.assert_prefixes(subscribe_mock, ("server", "weather"))

    def test_placeholder(self) -> None:
        """Placeholder to force pytest to generate a coverage file."""
        pass   # pylint: disable=unnecessary-pass


if __name__ == "__main__":
    unittest.main()
