"""Test suite for the combined_log parser."""

import unittest
import parsers.combined_log
from testing import helpers


class TestCombinedLogParser(unittest.TestCase):

    parser: parsers.combined_log.Parser

    @classmethod
    def setUpClass(cls) -> None:
        """Create the parser instance."""
        cls.parser = parsers.combined_log.Parser()

    def test_parse(self) -> None:
        """All fields of a typical log line are extracted as expected."""

        logline = helpers.get_fixture("combined.log")
        fields = self.parser.parse(logline)

        self.assertEqual(fields["ip"], "100.200.300.400")
        self.assertIsNone(fields["identity"])
        self.assertEqual(fields["user"], "fakeuser")
        self.assertEqual(fields["datestamp"], "1999-01-01-08")
        self.assertEqual(fields["unix_timestamp"], 915177661.0)
        self.assertEqual(fields["method"], "GET")
        self.assertEqual(fields["uri"], "/hello/world.html")
        self.assertEqual(fields["query"], "param1=value1&param2=value2")
        self.assertEqual(fields["http_version"], "HTTP/1.1")
        self.assertEqual(fields["statusCode"], 302)
        self.assertEqual(fields["numBytesSent"], 0)
        self.assertEqual(fields["referrer"], "http://example.com/page.html")
        self.assertEqual(fields["referrer_domain"], "example.com")
        self.assertEqual(
            fields["agent"],
            "Mozilla/5.0 (+http://www.example.com/bot.html)"
        )
        self.assertEqual(fields["host"], "example.com")
        self.assertEqual(fields["extras"]["request_id"], "abcdefg")
        self.assertEqual(fields["extras"]["city"], "New York")
        self.assertEqual(fields["extras"]["latitude"], "123")
        self.assertEqual(fields["extras"]["longitude"], "456")
        self.assertNotIn("region", fields["extras"].keys())

    def test_noreferrer_parse(self) -> None:
        """A logline without a referrer is parsed as expected."""

        logline = helpers.get_fixture("combined_noreferrer.log")
        fields = self.parser.parse(logline)
        self.assertIsNone(fields["referrer"])
        self.assertIsNone(fields["referrer_domain"])


if __name__ == "__main__":
    unittest.main()
