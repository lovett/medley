"""Test suite for the markup plugin."""

import unittest
from unittest.mock import Mock, patch
import cherrypy
import plugins.markup
from testing.assertions import Subscriber
from resources.url import Url


class TestMarkup(Subscriber):
    """Tests for the markup plugin."""

    def setUp(self) -> None:
        self.plugin = plugins.markup.Plugin(cherrypy.engine)

    @patch("cherrypy.engine.subscribe")
    def test_subscribe(self, subscribe_mock: Mock) -> None:
        """Subscriptions are prefixed consistently."""

        self.plugin.start()
        self.assert_prefix(subscribe_mock, "markup")

    def test_plain_text(self) -> None:
        """Markup is removed but text nodes are preserved."""
        result = self.plugin.plain_text("<b>hello <em>world</em></b>")
        self.assertEqual(result, "hello world")

    def test_plain_text_empty(self) -> None:
        """Empty input is handled."""
        result = self.plugin.plain_text("")
        self.assertEqual(result, "")

        result = self.plugin.plain_text(None)
        self.assertEqual(result, "")

    def test_plain_text_with_blacklist(self) -> None:
        """Site-specific tag blacklists cause text nodes to be dropped."""
        initial = '<div class="reply">hello <em>world</em></div>'
        result = self.plugin.plain_text(
            initial,
            Url("http://news.ycombinator.com/")
        )
        self.assertEqual(result, "")

        result = self.plugin.plain_text(initial)
        self.assertEqual(result, "hello world")


if __name__ == "__main__":
    unittest.main()
