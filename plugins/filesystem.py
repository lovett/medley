"""Filesystem interaction."""

import os
from pathlib import Path
from typing import Iterator
from typing import Tuple
import zipfile
import cherrypy


class Plugin(cherrypy.process.plugins.SimplePlugin):
    """A CherryPy plugin for filesystem interaction."""

    def __init__(self, bus: cherrypy.process.wspbus.Bus) -> None:
        cherrypy.process.plugins.SimplePlugin.__init__(self, bus)

    def start(self) -> None:
        """Define the CherryPy messages to listen for.

        This plugin owns the filesystem prefix.

        A zipfile is considered a filesystem for compatibility with
        running from inside a zipapp.

        """

        if cherrypy.config.get("zipapp"):
            self.bus.subscribe("filesystem:read", self.read_zip)
            self.bus.subscribe("filesystem:walk", self.walk_zip)
        else:
            self.bus.subscribe("filesystem:read", self.read_fs)
            self.bus.subscribe("filesystem:walk", self.walk_fs)

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
    def walk_zip(
            extensions: Tuple[str, ...]
    ) -> Iterator[Path]:
        """Walk the contents of a zipapp and filter by extension."""

        archive = Path(cherrypy.config.get("server_root"))

        with zipfile.ZipFile(archive) as handle:
            for name in handle.namelist():
                file_path = Path(name)
                extension = "".join(file_path.suffixes)

                if extension in extensions:
                    yield file_path

    @staticmethod
    def walk_fs(
            extensions: Tuple[str, ...]
    ) -> Iterator[Path]:
        """Walk the filesystem and filter by extension."""

        server_root = Path(cherrypy.config.get("server_root"))

        app_root = server_root / "apps"

        for root, _, files in os.walk(app_root):
            current_dir = Path(root).relative_to(server_root)

            for name in files:
                file_path = current_dir / name
                extension = "".join(file_path.suffixes)

                if extension in extensions:
                    yield file_path
