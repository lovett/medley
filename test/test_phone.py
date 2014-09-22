import util.phone
import unittest

class TestUtilPhone(unittest.TestCase):
    def test_sanitizeNumeric(self):
        """Numeric strings are returned untouched"""
        initial = "100"
        final = util.phone.sanitize(initial)
        self.assertEqual(final, initial)

    def test_sanitizeMixed(self):
        """Alphanumeric strings are reduced to numbers only"""
        initial = "This is a test 100"
        final = util.phone.sanitize(initial)
        self.assertEqual(final, "100")

    def test_sanitizeEmpty(self):
        """An empty string is returned untouched"""
        initial = ""
        final = util.phone.sanitize(initial)
        self.assertEqual(final, "")

    def test_formatEmpty(self):
        """An empty string is returned untouched"""
        initial = ""
        final = util.phone.format(initial)
        self.assertEqual(final, "")

    def test_formatTen(self):
        """A 10 digit number is formatted correctly"""
        initial = "1234567890"
        final = util.phone.format(initial)
        self.assertEqual(final, "(123) 456-7890")

    def test_formatSeven(self):
        """A 7 digit number is formatted correctly"""
        initial = "1234567"
        final = util.phone.format(initial)
        self.assertEqual(final, "123-4567")



if __name__ == '__main__':
    unittest.main()
