"""Test suite for the recipes plugin."""

import unittest
import cherrypy
import plugins.recipes


class TestRecipes(unittest.TestCase):
    """Tests for the recipes plugin."""

    def setUp(self) -> None:
        self.plugin = plugins.recipes.Plugin(cherrypy.engine)

    def test_placeholder(self) -> None:
        """Placeholder to force pytest to generate a coverage file."""
        pass   # pylint: disable=unnecessary-pass


if __name__ == "__main__":
    unittest.main()
