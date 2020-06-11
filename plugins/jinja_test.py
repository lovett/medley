"""Test suite for the jinja plugin."""

import unittest
from unittest.mock import Mock, patch
import cherrypy
import plugins.jinja
from testing.assertions import Subscriber


class TestJinja(Subscriber):
    """Tests for the jinja plugin."""

    def setUp(self) -> None:
        self.plugin = plugins.jinja.Plugin(cherrypy.engine)

    @patch("cherrypy.engine.subscribe")
    def test_subscribe(self, subscribe_mock: Mock) -> None:
        """Subscriptions are prefixed consistently."""

        self.plugin.start()
        self.assert_prefix(subscribe_mock, "jinja")

    def test_phonenumber_empty(self) -> None:
        """An empty string is returned untouched"""
        initial = ""
        final = self.plugin.phonenumber_filter(initial)
        self.assertEqual(final, "")

    def test_phonenumber_ten(self) -> None:
        """A 10 digit number is formatted correctly"""
        initial = "1234567890"
        final = self.plugin.phonenumber_filter(initial)
        self.assertEqual(final, "(123) 456-7890")

    def test_phonenumber_seven(self) -> None:
        """A 7 digit number is formatted correctly"""
        initial = "1234567"
        final = self.plugin.phonenumber_filter(initial)
        self.assertEqual(final, "123-4567")


if __name__ == "__main__":
    unittest.main()
