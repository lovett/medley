"""Test suite for the gcp_storage plugin."""

import unittest
import cherrypy
import plugins.gcp_storage


class TestGcpStorage(unittest.TestCase):
    """Tests for the gcp_storage plugin."""

    def setUp(self) -> None:
        self.plugin = plugins.gcp_storage.Plugin(cherrypy.engine)

    def test_placeholder(self) -> None:
        """Placeholder to force pytest to generate a coverage file."""
        pass   # pylint: disable=unnecessary-pass


if __name__ == "__main__":
    unittest.main()
