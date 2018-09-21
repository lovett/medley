"""Test suite for the html-to-text parser."""

import unittest
import parsers.htmlhead


class TestHtmlHeadParser(unittest.TestCase):
    """Tests for the html head parser."""

    parser = None

    @classmethod
    def setUpClass(cls):
        """Create the parser instance."""
        cls.parser = parsers.htmlhead.Parser()

    @classmethod
    def tearDownClass(cls):
        """Destroy the parser."""
        cls.parser = None

    def test_simple_parse(self):
        """A simplistic document is parsed successfully."""

        initial = """
        <html><head><title id="test">Hello world</title></head></html>
        """
        final = self.parser.parse(initial)

        self.assertEqual(final[0][0], "title")
        self.assertEqual(final[0][1][0][0], "id")
        self.assertEqual(final[0][1][0][1], "test")
        self.assertEqual(final[0][2], "Hello world")
        self.assertEqual(len(final[0]), 3)


if __name__ == "__main__":
    unittest.main()
