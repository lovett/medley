"""
Test suite for the cache plugin
"""

import unittest
import cherrypy
import plugins.cache


class TestCache(unittest.TestCase):
    """
    Tests for the cache plugin
    """

    def setUp(self):
        self.plugin = plugins.cache.Plugin(cherrypy.engine)

    def test_placeholder(self):
        """Placeholder to force pytest to generate a coverage file."""
        pass   # pylint: disable=unnecessary-pass


if __name__ == "__main__":
    unittest.main()
