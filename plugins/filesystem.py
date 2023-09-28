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
            wanted_extensions: Tuple[str, ...],
            excluded_dirs: Tuple[str, ...],
            excluded_files: Tuple[str, ...]
    ) -> Iterator[Path]:
        """Walk the filesystem and filter by extension."""

        if not wanted_extensions:
            return

        if not excluded_dirs:
            return

        server_root = cherrypy.config.get(
            "server_root",
            os.getcwd()
        )

        for root, dirs, files in os.walk(server_root, topdown=True):
            dirs[:] = [
                d for d in dirs
                if not d.startswith(".") and d not in excluded_dirs
            ]

            for file_name in files:
                if any(file_name.endswith(item) for item in excluded_files):
                    continue

                if any(file_name.endswith(ext) for ext in wanted_extensions):
                    yield Path(root) / file_name
