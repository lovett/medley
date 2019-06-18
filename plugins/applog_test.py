"""
Test suite for the applog plugin
"""

import unittest
import cherrypy
import plugins.applog


class TestUrl(unittest.TestCase):
    """
    Tests for the applog plugin
    """

    def setUp(self):
        self.plugin = plugins.url.Plugin(cherrypy.engine)

    def test_placeholder(self):
        """Placeholder to force pytest to generate a coverage file."""
        pass   # pylint: disable=unnecessary-pass


if __name__ == "__main__":
    unittest.main()
