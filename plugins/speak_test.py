"""Test suite for the speak plugin."""

import unittest
import cherrypy
import plugins.speak
from testing.assertions import Subscriber


class TestSpeak(Subscriber):
    """Tests for the speak plugin."""

    def setUp(self) -> None:
        self.plugin = plugins.speak.Plugin(cherrypy.engine)

    def test_placeholder(self) -> None:
        """Placeholder to force pytest to generate a coverage file."""
        pass   # pylint: disable=unnecessary-pass


if __name__ == "__main__":
    unittest.main()
