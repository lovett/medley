"""
Test suite for the mixins plugin
"""

import unittest
import cherrypy
import plugins.mixins


class TestUrl(unittest.TestCase):
    """
    Tests for the mixins plugin
    """

    def setUp(self):
        self.plugin = plugins.url.Plugin(cherrypy.engine)

    def test_placeholder(self):
        """Placeholder to force pytest to generate a coverage file."""
        pass   # pylint: disable=unnecessary-pass


if __name__ == "__main__":
    unittest.main()
