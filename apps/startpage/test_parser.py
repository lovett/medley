"""Test suite for the startpage parser."""

import unittest
from apps.startpage.parser import Parser


class TestStartpageParser(unittest.TestCase):
    """Tests for the config parser used by the startpage app."""

    @classmethod
    def setUp(cls):
        cls.parser = Parser()

    def parse(self, text):
        """Send a value to the parser."""
        return self.parser.parse(text)

    def test_basic_parsing(self):
        """A simplistic input parses successfully."""

        content = """[section1]
        key1 = value1
        key2 = value2"""

        config = self.parse(content)

        self.assertEqual(config["section1"]["key1"], "value1")
        self.assertEqual(config["section1"]["key2"], "value2")

    def test_duplicate_keys(self):
        """Duplicate keys within a section are allowed."""

        content = """[section1]
        key1 = value1
        key1 = value2"""

        config = self.parse(content)

        self.assertEqual(config["section1"]["key1"], "value2")

    def test_duplicate_secions(self):
        """Duplicate sections are allowed."""

        content = """[section1]
        key1 = value1

        [section1]
        key1 = value2"""

        config = self.parse(content)

        self.assertEqual(config["section1"]["key1"], "value2")

    def test_url_keys(self):
        """URLs are accepted as option keys."""

        content = """[section1]
        http://example.com = example"""

        config = self.parse(content)

        self.assertEqual(config["section1"]["http://example.com"], "example")
