"""Test suite for the custom jinja bytecode cache."""

import unittest
import plugins.jinja_cache


class TestJinja(unittest.TestCase):
    """Tests for the jinja plugin."""

    def setUp(self) -> None:
        self.cache = plugins.jinja_cache.Cache()

    def test_placeholder(self) -> None:
        """Placeholder to force pytest to generate a coverage file."""
        pass   # pylint: disable=unnecessary-pass


if __name__ == "__main__":
    unittest.main()
