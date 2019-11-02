"""
Test suite for the jinja plugin
"""

import unittest
import cherrypy
import plugins.jinja


class TestJinja(unittest.TestCase):
    """
    Tests for the jinja plugin.
    """

    def setUp(self):
        self.plugin = plugins.jinja.Plugin(cherrypy.engine)

    def test_phonenumber_empty(self):
        """An empty string is returned untouched"""
        initial = ""
        final = self.plugin.phonenumber_filter(initial)
        self.assertEqual(final, "")

    def test_phonenumber_ten(self):
        """A 10 digit number is formatted correctly"""
        initial = "1234567890"
        final = self.plugin.phonenumber_filter(initial)
        self.assertEqual(final, "(123) 456-7890")

    def test_phonenumber_seven(self):
        """A 7 digit number is formatted correctly"""
        initial = "1234567"
        final = self.plugin.phonenumber_filter(initial)
        self.assertEqual(final, "123-4567")


if __name__ == "__main__":
    unittest.main()
