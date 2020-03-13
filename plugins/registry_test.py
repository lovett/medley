"""Test suite for the registry plugin."""

import unittest
import cherrypy
import plugins.registry


class TestRegistry(unittest.TestCase):
    """Tests for the registry plugin."""

    def setUp(self) -> None:
        self.plugin = plugins.registry.Plugin(cherrypy.engine)

    def test_placeholder(self) -> None:
        """Placeholder to force pytest to generate a coverage file."""
        pass   # pylint: disable=unnecessary-pass


if __name__ == "__main__":
    unittest.main()
