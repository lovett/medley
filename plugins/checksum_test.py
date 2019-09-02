"""
Test suite for the checksum plugin
"""

import unittest
import cherrypy
import plugins.checksum


class TestChecksum(unittest.TestCase):
    """
    Tests for the checksum plugin
    """

    def setUp(self):
        self.plugin = plugins.checksum.Plugin(cherrypy.engine)

    def test_placeholder(self):
        """Placeholder to force pytest to generate a coverage file."""
        pass   # pylint: disable=unnecessary-pass


if __name__ == "__main__":
    unittest.main()
