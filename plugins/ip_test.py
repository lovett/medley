"""
Test suite for the ip plugin
"""

import unittest
import cherrypy
import plugins.ip


class TestIp(unittest.TestCase):
    """
    Tests for the ip plugin
    """

    def setUp(self):
        self.plugin = plugins.ip.Plugin(cherrypy.engine)

    def test_placeholder(self):
        """Placeholder to force pytest to generate a coverage file."""
        pass   # pylint: disable=unnecessary-pass


if __name__ == "__main__":
    unittest.main()
