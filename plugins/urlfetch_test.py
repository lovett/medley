"""
Test suite for the urlfetch plugin
"""

import unittest
import cherrypy
import plugins.urlfetch


class TestUrlfetch(unittest.TestCase):
    """
    Tests for the urlfetch plugin.
    """

    def setUp(self):
        self.plugin = plugins.urlfetch.Plugin(cherrypy.engine)

    def test_placeholder(self):
        """Placeholder to force pytest to generate a coverage file."""
        pass   # pylint: disable=unnecessary-pass


if __name__ == "__main__":
    unittest.main()
