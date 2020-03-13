"""Test suite for the cdr plugin."""

import unittest
import cherrypy
import plugins.cdr


class TestCdr(unittest.TestCase):
    """Tests for the cdr plugin."""

    def setUp(self) -> None:
        self.plugin = plugins.cdr.Plugin(cherrypy.engine)

    def test_placeholder(self) -> None:
        """Placeholder to force pytest to generate a coverage file."""
        pass   # pylint: disable=unnecessary-pass


if __name__ == "__main__":
    unittest.main()
