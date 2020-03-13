"""Test suite for the audio plugin."""

import unittest
import cherrypy
import plugins.audio


class TestAudio(unittest.TestCase):
    """Tests for the audio plugin."""

    def setUp(self) -> None:
        self.plugin = plugins.audio.Plugin(cherrypy.engine)

    def test_placeholder(self) -> None:
        """Placeholder to force pytest to generate a coverage file."""
        pass   # pylint: disable=unnecessary-pass


if __name__ == "__main__":
    unittest.main()
