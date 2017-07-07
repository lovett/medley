import unittest
from util.sqlite_converters import *

class TestUtilSqliteConverters(unittest.TestCase):

    def test_convertDate(self):
        """An ISO date string is parsed into a datetime object"""
        result = convert_date(b"2013-03-16 20:04:40")
        self.assertIsInstance(result, datetime.datetime)

    def test_convertDuration(self):
        """A integer number of seconds is converted to a string phrase"""

        result = convert_duration(0)
        self.assertEqual(result, "0 seconds")

        result = convert_duration(1)
        self.assertEqual(result, "1 second")

        result = convert_duration(60)
        self.assertEqual(result, "1 minute")

        result = convert_duration(61)
        self.assertEqual(result, "1 minute, 1 second")

        result = convert_duration(3600)
        self.assertEqual(result, "1 hour")

        result = convert_duration(3660)
        self.assertEqual(result, "1 hour, 1 minute")

        result = convert_duration(3661)
        self.assertEqual(result, "1 hour, 1 minute, 1 second")

        result = convert_duration(3601)
        self.assertEqual(result, "1 hour, 1 second")

        result = convert_duration(7200)
        self.assertEqual(result, "2 hours")

        result = convert_duration(121)
        self.assertEqual(result, "2 minutes, 1 second")

        result = convert_duration(86400 * 7)
        self.assertEqual(result, "168 hours")

    def test_convertCallerid(self):
        """The callerid name is correctly extracted from a callerid string"""
        result = convert_callerid(b'"Name" <123>')
        self.assertEqual(result, "Name")


if __name__ == '__main__':
    unittest.main()
