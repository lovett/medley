"""
Test suite for the formatting plugin
"""

import unittest
import cherrypy
import plugins.formatting


class TestFormatting(unittest.TestCase):
    """
    Tests for the formatting plugin
    """

    def setUp(self):
        self.plugin = plugins.formatting.Plugin(cherrypy.engine)

    def test_phone_sanitize_numeric(self):
        """Numeric strings are returned untouched"""
        initial = "100"
        final = self.plugin.phone_sanitize(initial)
        self.assertEqual(final, initial)

    def test_phone_sanitize_mixed(self):
        """Alphanumeric strings are reduced to numbers only"""

        initial = "This is a test 100"
        final = self.plugin.phone_sanitize(initial)
        self.assertEqual(final, "100")

    def test_phone_sanitize_empty(self):
        """An empty string is returned untouched"""
        initial = ""
        final = self.plugin.phone_sanitize(initial)
        self.assertEqual(final, "")


if __name__ == "__main__":
    unittest.main()
