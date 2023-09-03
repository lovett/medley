"""Test suite for the filesystem plugin."""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
import cherrypy
import plugins.filesystem
from testing.assertions import Subscriber


class TestFilesystem(Subscriber):

    def setUp(self) -> None:
        self.plugin = plugins.filesystem.Plugin(cherrypy.engine)

    @patch("cherrypy.engine.subscribe")
    def test_subscribe(self, subscribe_mock: Mock) -> None:
        """Subscriptions are prefixed consistently."""

        self.plugin.start()
        self.assert_prefix(subscribe_mock, "filesystem")

    @patch("cherrypy.engine.subscribe")
    def test_subscribe_fs(self, subscribe_mock: Mock) -> None:
        """Subscriptions for regular functions are prefixed
        consistently."""

        self.plugin.start()
        self.assert_prefix(subscribe_mock, "filesystem")

    def test_file_fs(self) -> None:
        """A file on the filesystem is returned as bytes."""

        with tempfile.NamedTemporaryFile(delete=False) as temp:
            temp.write(b"hello world")
            temp.close()

            result = self.plugin.read_fs(Path(temp.name))
            Path(temp.name).unlink()

        self.assertEqual(result, b"hello world")


if __name__ == "__main__":
    unittest.main()
