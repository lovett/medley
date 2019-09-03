"""Test suite for the startpage parser."""

import unittest
import parsers.startpage


class TestStartpageParser(unittest.TestCase):
    """Tests for the config parser used by the startpage app."""

    anonymizer_url = "http://a.example.com?u="

    @classmethod
    def setUp(cls):
        cls.parser = parsers.startpage.Parser()
        cls.anonParser = parsers.startpage.Parser(
            cls.anonymizer_url,
            ["localhost"]
        )

    def test_basic_parsing(self):
        """A simplistic input parses successfully."""

        content = """[section1]
        key1 = value1
        key2 = value2"""

        config = self.parser.parse(content)

        self.assertEqual(config["section1"]["key1"], "value1")
        self.assertEqual(config["section1"]["key2"], "value2")

    def test_duplicate_keys(self):
        """Duplicate keys within a section are allowed."""

        content = """[section1]
        key1 = value1
        key1 = value2"""

        config = self.parser.parse(content)

        self.assertEqual(config["section1"]["key1"], "value2")

    def test_duplicate_secions(self):
        """Duplicate sections are allowed."""

        content = """[section1]
        key1 = value1

        [section1]
        key1 = value2"""

        config = self.parser.parse(content)

        self.assertEqual(config["section1"]["key1"], "value2")

    def test_url_keys(self):
        """URLs are accepted as option keys."""

        content = """[section1]
        http://example.com = example"""

        config = self.parser.parse(content)

        self.assertEqual(
            config.get("section1", "http://example.com"),
            "example"
        )

    def test_anonymizer_prepend(self):
        """URLs are prepended with the anonymizer URL.

        Anonymized URLs are also escaped.

        """

        content = """[section1]
        http://example.com?key1=value1 = example"""

        config = self.anonParser.parse(content)

        self.assertIn(
            f"{self.anonymizer_url}http%3A//example.com%3Fkey1%3Dvalue1",
            list(config["section1"].keys())
        )

    def test_anonymizer_skips_local(self):
        """URLs are not anonymized if they match one of the values specified
        as a local domain.

        """

        content = """[section1]
        http://localhost = localhost"""

        config = self.anonParser.parse(content)

        self.assertEqual(
            ['http://localhost'],
            list(config["section1"].keys())
        )
