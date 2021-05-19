"""Test suite for the jinja plugin."""

import typing
import unittest
from unittest import mock
import cherrypy
import plugins.jinja
from testing.assertions import Subscriber


class TestJinja(Subscriber):
    """Tests for the jinja plugin."""

    def setUp(self) -> None:
        self.plugin = plugins.jinja.Plugin(cherrypy.engine)

    @mock.patch("cherrypy.engine.subscribe")
    def test_subscribe(self, subscribe_mock: mock.Mock) -> None:
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

    @mock.patch("cherrypy.engine.publish")
    def test_autolink(self, publish_mock: mock.Mock) -> None:
        """Autolinking detects URLs."""

        def side_effect(*args: str, **_: str) -> typing.Any:
            """Side effects local function"""
            if args[0] == "url:internal":
                return ["/test"]

            return mock.DEFAULT
        publish_mock.side_effect = side_effect

        initial = "http://example.com"
        final = self.plugin.autolink_filter(initial)
        self.assertIn("<a href=", final)

        initial = "no link here"
        final = self.plugin.autolink_filter(initial)
        self.assertNotIn("<a href=", final)

    def test_autolink_empty_value(self) -> None:
        """Autolinking doesn't throw if the value is empty."""

        initial = None
        final = self.plugin.autolink_filter(initial)
        self.assertEqual(final, "")


if __name__ == "__main__":
    unittest.main()
