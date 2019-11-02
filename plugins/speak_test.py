"""
Test suite for the speak plugin
"""

import unittest
import cherrypy
import plugins.speak


class TestSpeak(unittest.TestCase):
    """
    Tests for the speak plugin.
    """

    def setUp(self):
        self.plugin = plugins.speak.Plugin(cherrypy.engine)

    def test_placeholder(self):
        """Placeholder to force pytest to generate a coverage file."""
        pass   # pylint: disable=unnecessary-pass


if __name__ == "__main__":
    unittest.main()
