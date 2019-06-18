"""
Test suite for the capture plugin
"""

import unittest
import cherrypy
import plugins.capture


class TestUrl(unittest.TestCase):
    """
    Tests for the capture plugin
    """

    def setUp(self):
        self.plugin = plugins.url.Plugin(cherrypy.engine)

    def test_placeholder(self):
        """Placeholder to force pytest to generate a coverage file."""
        pass   # pylint: disable=unnecessary-pass


if __name__ == "__main__":
    unittest.main()
