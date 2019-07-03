"""
Test suite for the registry plugin
"""

import unittest
import cherrypy
import plugins.registry


class TestUrl(unittest.TestCase):
    """
    Tests for the registry plugin
    """

    def setUp(self):
        self.plugin = plugins.url.Plugin(cherrypy.engine)

    def test_placeholder(self):
        """Placeholder to force pytest to generate a coverage file."""
        pass   # pylint: disable=unnecessary-pass


if __name__ == "__main__":
    unittest.main()