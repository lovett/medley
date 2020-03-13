"""Test suite for the capture plugin."""

import unittest
import cherrypy
import plugins.capture


class TestCapture(unittest.TestCase):
    """Tests for the capture plugin."""

    def setUp(self) -> None:
        self.plugin = plugins.capture.Plugin(cherrypy.engine)

    def test_placeholder(self) -> None:
        """Placeholder to force pytest to generate a coverage file."""
        pass   # pylint: disable=unnecessary-pass


if __name__ == "__main__":
    unittest.main()
