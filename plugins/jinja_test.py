"""Test suite for the jinja plugin."""

from typing import Any
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

        def side_effect(*args: str, **_: str) -> Any:
            if args[0] == "app_url":
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

    @mock.patch("cherrypy.engine.publish")
    def test_betterhtml_link_rewrite(self, publish_mock: mock.Mock) -> None:
        """HTML cleanup should not mangle links."""

        def side_effect(*args: str, **_: str) -> Any:
            if args[0] == "app_url":
                return [""]

            return mock.DEFAULT
        publish_mock.side_effect = side_effect

        # pylint: disable=line-too-long
        test_suite = [
            # Bare URL
            ("""Before http://example.com after""",
             """Before <a target="_blank" rel="noopener noreferrer" href="http://example.com">http://example.com</a> after"""),  # noqa: E501

            # Bare URL with other URL in path
            ("""Before http://example.com/http://example.net after""",
             """Before <a target="_blank" rel="noopener noreferrer" href="http://example.com/http://example.net">http://example.com/http://example.net</a> after"""),  # noqa: E501

            # Linked URL
            ("""Before <a href="http://example.com">link</a>""",
             """Before <a href="http://example.com">link</a>"""),

            # Linked URL with other URL in path
            ("""Before <a href="http://example.com/http://example.net">link</a>""",  # noqa: E501
             """Before <a href="http://example.com/http://example.net">link</a>"""),  # noqa: E501

            # Multiple URLs
            ("""Before http://example.com http://example.net after""",
             """Before <a target="_blank" rel="noopener noreferrer" href="http://example.com">http://example.com</a> <a target="_blank" rel="noopener noreferrer" href="http://example.net">http://example.net</a> after""")  # noqa: E501
        ]

        for key, value in test_suite:
            self.assertEqual(
                self.plugin.better_html_filter(key),
                value
            )


if __name__ == "__main__":
    unittest.main()
