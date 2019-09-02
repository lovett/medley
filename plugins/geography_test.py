"""
Test suite for the geography plugin
"""

import unittest
import cherrypy
import plugins.geography


class TestGeography(unittest.TestCase):
    """
    Tests for the geography plugin
    """

    def setUp(self):
        self.plugin = plugins.geography.Plugin(cherrypy.engine)

    def test_placeholder(self):
        """Placeholder to force pytest to generate a coverage file."""
        pass   # pylint: disable=unnecessary-pass


if __name__ == "__main__":
    unittest.main()
