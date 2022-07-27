"""Serve static files from Sqlite."""

import mimetypes
from pathlib import Path
from typing import Tuple
from typing import cast
import cherrypy
from plugins import mixins


class Plugin(cherrypy.process.plugins.SimplePlugin, mixins.Sqlite):
    """A CherryPy plugin for serving static files from Sqlite."""

    def __init__(self, bus: cherrypy.process.wspbus.Bus) -> None:
        cherrypy.process.plugins.SimplePlugin.__init__(self, bus)

        self.db_path = self._path("assets.sqlite")

        self._create("""
        PRAGMA journal_mode=WAL;
        PRAGMA foreign_keys=ON;

        CREATE TABLE IF NOT EXISTS assets (
            extension TEXT,
            path TEXT,
            mimetype TEXT,
            hash TEXT,
            bytes BLOB
        );

        CREATE INDEX IF NOT EXISTS index_extension
            ON assets(extension);

        """)

    def start(self) -> None:
        """Define the CherryPy messages to listen for.

        This plugin owns the assets prefix.

        """
        self.bus.subscribe("assets:get", self.asset_from_fs)
        self.bus.subscribe("assets:hash", self.hash_from_fs)

    @staticmethod
    def hash_from_fs(target: Path) -> str:
        """Calculate the hash of an asset on the filesystem."""

        return cast(
            str,
            cherrypy.engine.publish(
                "hasher:file",
                str(target)
            ).pop()
        )

    @staticmethod
    def asset_from_fs(target: Path) -> Tuple[bytes, str]:
        """Read an asset from the filesystem."""

        asset_bytes = cherrypy.engine.publish(
            "filesystem:read",
            target
        ).pop()

        mime_type, _ = mimetypes.guess_type(target.name)

        if not mime_type:
            mime_type = "application/octet-stream"

        return (asset_bytes, mime_type)
