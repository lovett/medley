"""
Test suite for the bookmarks plugin
"""

import unittest
import cherrypy
import plugins.bookmarks


class TestBookmarks(unittest.TestCase):
    """
    Tests for the bookmarks plugin
    """

    def setUp(self):
        self.plugin = plugins.bookmarks.Plugin(cherrypy.engine)

    def test_placeholder(self):
        """Placeholder to force pytest to generate a coverage file."""
        pass   # pylint: disable=unnecessary-pass


if __name__ == "__main__":
    unittest.main()
