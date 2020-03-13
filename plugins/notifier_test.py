"""Test suite for the notifier plugin."""

import unittest
import cherrypy
import plugins.notifier


class TestNotifier(unittest.TestCase):
    """Tests for the notifier plugin."""

    def setUp(self) -> None:
        self.plugin = plugins.notifier.Plugin(cherrypy.engine)

    def test_placeholder(self) -> None:
        """Placeholder to force pytest to generate a coverage file."""
        pass   # pylint: disable=unnecessary-pass


if __name__ == "__main__":
    unittest.main()
