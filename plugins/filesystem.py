"""Filesystem interaction."""

import os
from pathlib import Path
from typing import Iterator
from typing import Tuple
import cherrypy


class Plugin(cherrypy.process.plugins.SimplePlugin):
    """A CherryPy plugin for filesystem interaction."""

    def __init__(self, bus: cherrypy.process.wspbus.Bus) -> None:
        cherrypy.process.plugins.SimplePlugin.__init__(self, bus)

    def start(self) -> None:
        """Define the CherryPy messages to listen for.

        This plugin owns the filesystem prefix."""

        self.bus.subscribe("filesystem:read", self.read_fs)
        self.bus.subscribe("filesystem:walk", self.walk_fs)

    @staticmethod
    def read_fs(target: Path) -> bytes:
        """Read a file from the filesystem."""

        if not target.is_absolute():
            target = Path(cherrypy.config.get("server_root")) / target

        return target.read_bytes()

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
