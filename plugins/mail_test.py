"""Test suite for the mail plugin"""

import unittest
import cherrypy
import plugins.mail


class TestMail(unittest.TestCase):
    """
    Tests for the mail plugin.
    """

    def setUp(self) -> None:
        self.plugin = plugins.mail.Plugin(cherrypy.engine)

    def test_placeholder(self) -> None:
        """Placeholder to force pytest to generate a coverage file."""
        pass   # pylint: disable=unnecessary-pass


if __name__ == "__main__":
    unittest.main()
