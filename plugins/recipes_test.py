"""Test suite for the recipes plugin."""

import unittest
from unittest.mock import Mock, patch
import cherrypy
import plugins.recipes
from testing.assertions import Subscriber


class TestRecipes(Subscriber):
    """Tests for the recipes plugin."""

    def setUp(self) -> None:
        self.plugin = plugins.recipes.Plugin(cherrypy.engine)

    @patch("cherrypy.engine.subscribe")
    def test_subscribe(self, subscribe_mock: Mock) -> None:
        """Subscriptions are prefixed consistently."""

        self.plugin.start()
        self.assert_prefix(subscribe_mock, "recipes")

    def test_placeholder(self) -> None:
        """Placeholder to force pytest to generate a coverage file."""
        pass   # pylint: disable=unnecessary-pass


if __name__ == "__main__":
    unittest.main()
