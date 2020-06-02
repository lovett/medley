"""Test suite for the converters plugin."""

import unittest
import cherrypy
import plugins.converters


class TestConverters(unittest.TestCase):
    """Tests for the converters plugin."""

    def setUp(self) -> None:
        self.plugin = plugins.converters.Plugin(cherrypy.engine)

    def test_duration(self) -> None:
        """A integer number of seconds is converted to a string phrase"""

        result = self.plugin.duration(b"0")
        self.assertEqual(result, "0 seconds")

        result = self.plugin.duration(b"1")
        self.assertEqual(result, "1 second")

        result = self.plugin.duration(b"60")
        self.assertEqual(result, "1 minute")

        result = self.plugin.duration(b"61")
        self.assertEqual(result, "61 seconds")

        result = self.plugin.duration(b"3600")
        self.assertEqual(result, "1 hour")

        result = self.plugin.duration(b"3660")
        self.assertEqual(result, "1 hour, 1 minute")

        result = self.plugin.duration(b"3661")
        self.assertEqual(result, "1 hour, 1 minute, 1 second")

        result = self.plugin.duration(b"3601")
        self.assertEqual(result, "1 hour, 1 second")

        result = self.plugin.duration(b"7200")
        self.assertEqual(result, "2 hours")

        result = self.plugin.duration(b"121")
        self.assertEqual(result, "2 minutes, 1 second")

        result = self.plugin.duration(b"604800")
        self.assertEqual(result, "168 hours")

    def test_callerid(self) -> None:
        """The callerid name is correctly extracted from a callerid string"""
        result = self.plugin.callerid(b'"Name" <123>')
        self.assertEqual(result, "Name")


if __name__ == "__main__":
    unittest.main()
