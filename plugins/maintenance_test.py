"""Test suite for the maintenance plugin."""

import unittest
import cherrypy
import plugins.maintenance


class TestMaintenance(unittest.TestCase):
    """Tests for the maintenance plugin."""

    def setUp(self) -> None:
        self.plugin = plugins.maintenance.Plugin(cherrypy.engine)

    def test_placeholder(self) -> None:
        """Placeholder to force pytest to generate a coverage file."""
        pass   # pylint: disable=unnecessary-pass


if __name__ == "__main__":
    unittest.main()
