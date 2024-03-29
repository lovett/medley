"""Test suite for the html-to-text parser."""

import unittest
import parsers.htmlhead


class TestHtmlHeadParser(unittest.TestCase):

    parser: parsers.htmlhead.Parser

    @classmethod
    def setUp(cls) -> None:
        """Create the parser instance."""
        cls.parser = parsers.htmlhead.Parser()

    def test_simple_parse(self) -> None:
        """A reasonably-structured document is parsed successfully."""

        initial = """
        <html>
        <head>
            <title id="test">Hello world</title>
            <meta name="keyword" content="whatever" />
        </head>
        </html>
        """
        final = self.parser.parse(initial)

        self.assertEqual(final[0][0], "title")
        self.assertEqual(final[0][1][0][0], "id")
        self.assertEqual(final[0][1][0][1], "test")
        self.assertEqual(final[0][2], "Hello world")
        self.assertEqual(len(final[0]), 3)
        self.assertEqual(len(final), 2)

    def test_no_head(self) -> None:
        """A document with no head is parsed successfully."""

        initial = """
        <html>this is weird</html>
        """
        final = self.parser.parse(initial)

        self.assertEqual(len(final), 0)

    def test_entity(self) -> None:
        """Entities are converted during parsing."""

        initial = """
        <html><head><title>hello &gt; world</title></head></html>
        """
        final = self.parser.parse(initial)

        self.assertEqual(final[0][2], "hello > world")

    def test_only_head(self) -> None:
        """Tags outside the head are ignored."""

        initial = """
        <html>
        <head>
            <title>hello world</title>
        </head>
        <body>this is ignored</body>
        </html>
        """
        final = self.parser.parse(initial)

        self.assertEqual(len(final), 1)

    def test_malformed(self) -> None:
        """A malformed document is parsed successfully."""

        initial = """
        <html>
        <head>
            <invalid>
            <title>hello world</title>
        </head>
        </html>
        """
        final = self.parser.parse(initial)

        self.assertEqual(len(final), 1)


if __name__ == "__main__":
    unittest.main()
