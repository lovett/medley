"""
Test suite for the converters plugin
"""

import unittest
import cherrypy
import pendulum
import plugins.converters


class TestConverters(unittest.TestCase):
    """
    Tests for the converters plugin.
    """

    def setUp(self):
        self.plugin = plugins.converters.Plugin(cherrypy.engine)

    def test_duration(self):
        """A integer number of seconds is converted to a string phrase"""

        result = self.plugin.duration(0)
        self.assertEqual(result, "0 seconds")

        result = self.plugin.duration(1)
        self.assertEqual(result, "1 second")

        result = self.plugin.duration(60)
        self.assertEqual(result, "1 minute")

        result = self.plugin.duration(61)
        self.assertEqual(result, "1 minute, 1 second")

        result = self.plugin.duration(3600)
        self.assertEqual(result, "1 hour")

        result = self.plugin.duration(3660)
        self.assertEqual(result, "1 hour, 1 minute")

        result = self.plugin.duration(3661)
        self.assertEqual(result, "1 hour, 1 minute, 1 second")

        result = self.plugin.duration(3601)
        self.assertEqual(result, "1 hour, 1 second")

        result = self.plugin.duration(7200)
        self.assertEqual(result, "2 hours")

        result = self.plugin.duration(121)
        self.assertEqual(result, "2 minutes, 1 second")

        result = self.plugin.duration(86400 * 7)
        self.assertEqual(result, "168 hours")

    def test_datetime(self):
        """An ISO date string is parsed into a datetime object"""
        result = self.plugin.datetime(b"2013-03-16 20:04:40")
        self.assertEqual(
            result,
            pendulum.datetime(2013, 3, 16, 20, 4, 40)
        )

    def test_callerid(self):
        """The callerid name is correctly extracted from a callerid string"""
        result = self.plugin.callerid(b'"Name" <123>')
        self.assertEqual(result, "Name")


if __name__ == "__main__":
    unittest.main()
