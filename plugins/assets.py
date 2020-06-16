"""Serve static files from Sqlite."""

from pathlib import Path
import typing
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
            path TEXT NOT NULL,
            hash TEXT DEFAULT NULL,
            bytes BLOB DEFAULT NULL
        );

        CREATE UNIQUE INDEX IF NOT EXISTS index_path
            ON assets(path);

        """)

    def start(self) -> None:
        """Define the CherryPy messages to listen for.

        This plugin owns the assets prefix.

        """

        self.bus.subscribe("assets:get", self.get_asset)
        self.bus.subscribe("assets:hash", self.get_hash)
        self.bus.subscribe("assets:publish", self.publish)

    def get_hash(self, target: Path) -> str:
        """Read an asset's hash from the database."""

        print(f"get hash {target}")

        asset_hash = typing.cast(str, self._selectFirst(
            "SELECT hash FROM assets WHERE path=?",
            (str(target),)
        ))

        return asset_hash or ""

    def get_asset(self, target: Path) -> bytes:
        """Read a published asset from the database."""

        asset = typing.cast(bytes, self._selectFirst(
            "SELECT bytes FROM assets WHERE path=?",
            (str(target),)
        ))

        return asset or b""

    def publish(self) -> None:
        """Copy files from the filesystem to the database."""

        self._execute("DELETE FROM assets")

        insert_sql = """INSERT OR REPLACE INTO assets
        (path, hash, bytes)
        VALUES (?, ?, ?)"""

        batch = []
        asset_count = 0
        batch_size = 50

        walker = cherrypy.engine.publish(
            "filesystem:walk",
            (".css", ".js", ".svg", ".jinja.html")
        ).pop()

        for file_path in walker:
            file_bytes = cherrypy.engine.publish(
                "filesystem:read",
                file_path
            ).pop()

            file_hash = cherrypy.engine.publish(
                "hasher:value",
                file_bytes
            ).pop()

            batch.append(
                (insert_sql,
                 (str(file_path),
                  file_hash,
                  file_bytes)))

            if len(batch) > batch_size:
                self._multi(batch)
                asset_count += len(batch)
                batch = []

        if len(batch) > 0:
            self._multi(batch)
            asset_count += len(batch)
            batch = []
