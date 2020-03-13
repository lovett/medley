"""Test suite for the startpage parser."""

import unittest
import parsers.startpage


class TestStartpageParser(unittest.TestCase):
    """Tests for the startpage parser."""

    parser: parsers.startpage.Parser
    anon_parser: parsers.startpage.Parser

    anonymizer_url = "http://a.example.com?u="

    @classmethod
    def setUp(cls) -> None:
        cls.parser = parsers.startpage.Parser()
        cls.anon_parser = parsers.startpage.Parser(
            cls.anonymizer_url,
            ("localhost",)
        )

    def test_basic_parsing(self) -> None:
        """A simplistic input parses successfully."""

        content = """[section1]
        key1 = value1
        key2 = value2"""

        config = self.parser.parse(content)

        self.assertEqual(config["section1"]["key1"], "value1")
        self.assertEqual(config["section1"]["key2"], "value2")

    def test_duplicate_keys(self) -> None:
        """Duplicate keys within a section are allowed."""

        content = """[section1]
        key1 = value1
        key1 = value2"""

        config = self.parser.parse(content)

        self.assertEqual(config["section1"]["key1"], "value2")

    def test_duplicate_secions(self) -> None:
        """Duplicate sections are allowed."""

        content = """[section1]
        key1 = value1

        [section1]
        key1 = value2"""

        config = self.parser.parse(content)

        self.assertEqual(config["section1"]["key1"], "value2")

    def test_url_keys(self) -> None:
        """URLs are accepted as option keys."""

        content = """[section1]
        http://example.com = example"""

        config = self.parser.parse(content)

        self.assertEqual(
            config.get("section1", "http://example.com"),
            "example"
        )

    def test_anonymizer_prepend(self) -> None:
        """URLs are prepended with the anonymizer URL.

        Anonymized URLs are also escaped.

        """

        content = """[section1]
        http://example.com?key1=value1 = example"""

        config = self.anon_parser.parse(content)

        self.assertIn(
            f"{self.anonymizer_url}http%3A//example.com%3Fkey1%3Dvalue1",
            list(config["section1"].keys())
        )

    def test_anonymizer_skips_local(self) -> None:
        """URLs are not anonymized if they match one of the values specified
        as a local domain.

        """

        content = """[section1]
        http://localhost = localhost"""

        config = self.anon_parser.parse(content)

        self.assertEqual(
            ['http://localhost'],
            list(config["section1"].keys())
        )
