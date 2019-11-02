"""
Test suite for the logindex plugin
"""

import unittest
import cherrypy
import plugins.logindex


class TestLogindex(unittest.TestCase):
    """
    Tests for the logindex plugin.
    """

    def setUp(self):
        self.plugin = plugins.logindex.Plugin(cherrypy.engine)

    def test_placeholder(self):
        """Placeholder to force pytest to generate a coverage file."""
        pass   # pylint: disable=unnecessary-pass


if __name__ == "__main__":
    unittest.main()
