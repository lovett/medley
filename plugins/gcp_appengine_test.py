"""
Test suite for the gcp_appengine plugin
"""

import unittest
import cherrypy
import plugins.gcp_appengine


class TestGcpApengine(unittest.TestCase):
    """
    Tests for the gcp_appengine plugin.
    """

    def setUp(self):
        self.plugin = plugins.gcp_appengine.Plugin(cherrypy.engine)

    def test_placeholder(self):
        """Placeholder to force pytest to generate a coverage file."""
        pass   # pylint: disable=unnecessary-pass


if __name__ == "__main__":
    unittest.main()
