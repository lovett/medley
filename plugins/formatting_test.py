"""Test suite for the formatting plugin."""

import unittest
from unittest.mock import Mock, patch
import cherrypy
import plugins.formatting
from testing.assertions import Subscriber


class TestFormatting(Subscriber):
    """Tests for the formatting plugin."""

    def setUp(self) -> None:
        self.plugin = plugins.formatting.Plugin(cherrypy.engine)

    @patch("cherrypy.engine.subscribe")
    def test_subscribe(self, subscribe_mock: Mock) -> None:
        """Subscriptions are prefixed consistently."""

        self.plugin.start()
        self.assert_prefix(subscribe_mock, "formatting")

    def test_phone_sanitize_numeric(self) -> None:
        """Numeric strings are returned untouched"""
        initial = "100"
        final = self.plugin.phone_sanitize(initial)
        self.assertEqual(final, initial)

    def test_phone_sanitize_mixed(self) -> None:
        """Alphanumeric strings are reduced to numbers only"""

        initial = "This is a test 100"
        final = self.plugin.phone_sanitize(initial)
        self.assertEqual(final, "100")

    def test_phone_sanitize_empty(self) -> None:
        """An empty string is returned untouched"""

        initial = ""
        final = self.plugin.phone_sanitize(initial)
        self.assertEqual(final, "")

    def test_dbpedia_truncation(self) -> None:
        """A comment with two sentences is reduced to the first two"""

        initial = "First. Second. Third. Fourth. Fifth."
        final = self.plugin.dbpedia_abstract(initial)
        self.assertEqual(final, "First. Second.")

    def test_dbpedia_punctuation(self) -> None:
        """The abbreviated comment has correct punctuation"""

        initial = "Punctuation is missing"
        final = self.plugin.dbpedia_abstract(initial)
        self.assertEqual(final, initial + ".")

    def test_dbpedia_noise(self) -> None:
        """Noise is removed from the abbreviated comment"""

        initial = """The map to the right is now clickable;
        click on an area code to go to the map for that code."""
        final = self.plugin.dbpedia_abstract(initial)
        self.assertEqual(final, "")


if __name__ == "__main__":
    unittest.main()
