"""
Test suite for the metrics plugin
"""

import unittest
import cherrypy
import plugins.metrics


class TestMetrics(unittest.TestCase):
    """
    Tests for the metrics plugin.
    """

    def setUp(self):
        self.plugin = plugins.metrics.Plugin(cherrypy.engine)

    def test_placeholder(self):
        """Placeholder to force pytest to generate a coverage file."""
        pass   # pylint: disable=unnecessary-pass


if __name__ == "__main__":
    unittest.main()
