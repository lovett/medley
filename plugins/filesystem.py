"""Filesystem interaction."""

from pathlib import Path
import typing
import zipfile
import cherrypy


class Plugin(cherrypy.process.plugins.SimplePlugin):
    """A CherryPy plugin for filesystem interaction."""

    def __init__(self, bus: cherrypy.process.wspbus.Bus) -> None:
        cherrypy.process.plugins.SimplePlugin.__init__(self, bus)

    def start(self) -> None:
        """Define the CherryPy messages to listen for.

        A zipfile is considered a filesystem for compatibility with
        running from inside a zipapp.

        This plugin owns the filesystem prefix.

        """

        if cherrypy.config.get("zipapp"):
            self.bus.subscribe("filesystem:read", self.read_zip)
            self.bus.subscribe("filesystem:hash", self.hash_zip)
        else:
            self.bus.subscribe("filesystem:read", self.read_fs)
            self.bus.subscribe("filesystem:hash", self.hash_fs)

    @staticmethod
    def read_fs(target: Path) -> bytes:
        """Read a file from the filesystem."""

        if not target.is_file():
            return b""

        return target.read_bytes()

    @staticmethod
    def read_zip(target: Path) -> bytes:
        """Read a file from a ZIP archive."""

        archive = Path(cherrypy.config.get("server_root"))

        if not archive.is_file():
            return b""

        with zipfile.ZipFile(archive) as handle:
            try:
                zipinfo = handle.getinfo(str(target))
                return handle.read(zipinfo)
            except KeyError:
                return b""

    @staticmethod
    def hash_fs(target: str) -> str:
        """Get the hash of a file from the filesystem."""
        return typing.cast(
            str,
            cherrypy.engine.publish(
                "hasher:file",
                target
            ).pop()
        )

    def hash_zip(self, target: Path) -> str:
        """Get the hash of a file in a ZIP archive."""

        file_contents = self.read_zip(target)

        return typing.cast(
            str,
            cherrypy.engine.publish(
                "hasher:value",
                file_contents
            ).pop()
        )
