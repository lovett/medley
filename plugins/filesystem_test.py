"""Test suite for the filesystem plugin."""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
from zipfile import ZipFile
import cherrypy
import plugins.filesystem
from testing.assertions import Subscriber


class TestFilesystem(Subscriber):
    """Tests for the filesystem plugin."""

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

    @patch("cherrypy.engine.subscribe")
    def test_subscribe_zip(self, subscribe_mock: Mock) -> None:
        """Subscriptions for zip functions are prefixed
        consistently."""

        cherrypy.config.update({"zipapp": True})
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

    def test_file_fs_nonexistant(self) -> None:
        """No exception is raised if a file does not exist."""

        with tempfile.NamedTemporaryFile() as temp:
            temp.close()

            result = self.plugin.read_fs(Path(temp.name))
        self.assertEqual(result, b"")

    def test_file_zip(self) -> None:
        """A file in a ZIP archive is returned as bytes."""
        with tempfile.NamedTemporaryFile(delete=False) as tmpfile:
            tmpfile.write(b"hello world")
            tmpfile.close()

            with tempfile.NamedTemporaryFile(delete=False) as tmpzip:
                with ZipFile(tmpzip.name, "w") as handle:
                    handle.write(tmpfile.name)

                cherrypy.config.update({"server_root": tmpzip.name})

            zipfile_path = Path(tmpfile.name).relative_to("/")
            result = self.plugin.read_zip(zipfile_path)
            Path(tmpzip.name).unlink()
            Path(tmpfile.name).unlink()

        self.assertEqual(result, b"hello world")

    def test_file_zip_nonexistant(self) -> None:
        """No exception is raised if a file does not exist."""

        with tempfile.NamedTemporaryFile(delete=False) as tmpfile:
            tmpfile.write(b"hello world")
            tmpfile.close()

            with tempfile.NamedTemporaryFile(delete=False) as tmpzip:
                with ZipFile(tmpzip.name, "w") as handle:
                    handle.write(tmpfile.name)

                cherrypy.config.update({"server_root": tmpzip.name})

                result = self.plugin.read_zip(Path("a/b/c/d/e"))
                self.assertEqual(result, b"")
                Path(tmpzip.name).unlink()
            Path(tmpfile.name).unlink()

            cherrypy.config.update({"server_root": ""})

            result = self.plugin.read_zip(Path("f/g/h"))
            self.assertEqual(result, b"")


if __name__ == "__main__":
    unittest.main()
