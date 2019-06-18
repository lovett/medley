"""
Test suite for the hasher plugin
"""

import unittest
import cherrypy
import plugins.hasher


class TestUrl(unittest.TestCase):
    """
    Tests for the hasher plugin
    """

    def setUp(self):
        self.plugin = plugins.url.Plugin(cherrypy.engine)

    def test_placeholder(self):
        """Placeholder to force pytest to generate a coverage file."""
        pass   # pylint: disable=unnecessary-pass


if __name__ == "__main__":
    unittest.main()
