"""Serve static files from Sqlite."""

import mimetypes
from pathlib import Path
import typing
import cherrypy
from plugins import mixins, decorators


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

        if cherrypy.config.get("zipapp"):
            self.bus.subscribe("assets:get", self.asset_from_db)
            self.bus.subscribe("assets:hash", self.hash_from_db)
            self.bus.subscribe("assets:publish", self.publish)
        else:
            self.bus.subscribe("assets:get", self.asset_from_fs)
            self.bus.subscribe("assets:hash", self.hash_from_fs)

    def hash_from_db(self, target: Path) -> str:
        """Retrieve a published asset's hash."""

        asset_hash = typing.cast(str, self._selectFirst(
            "SELECT hash FROM assets WHERE extension=? AND path=?",
            (target.suffix.lstrip("."), str(target),)
        ))

        return asset_hash or ""

    @staticmethod
    def hash_from_fs(target: Path) -> str:
        """Calculate the hash of an asset on the filesystem."""

        return typing.cast(
            str,
            cherrypy.engine.publish(
                "hasher:file",
                str(target)
            ).pop()
        )

    def asset_from_db(self, target: Path) -> typing.Tuple[bytes, str]:
        """Retrieve a published asset and its mimetype."""

        row = self._selectOne(
            "SELECT bytes, mimetype FROM assets WHERE extension=? AND path=?",
            (target.suffix.lstrip("."), str(target))
        )

        if not row:
            return (b"", "")

        return (
            typing.cast(bytes, row["bytes"]),
            typing.cast(str, row["mimetype"])
        )

    @staticmethod
    def asset_from_fs(target: Path) -> typing.Tuple[bytes, str]:
        """Rad an asset from the filesystem."""

        asset_bytes = cherrypy.engine.publish(
            "filesystem:read",
            target
        ).pop()

        mime_type, _ = mimetypes.guess_type(target.name)

        if not mime_type:
            mime_type = "application/octet-stream"

        return (asset_bytes, mime_type)

    @decorators.log_runtime
    def publish(self) -> None:
        """Copy files from the filesystem to the database."""

        self._execute("DELETE FROM assets")

        insert_sql = """INSERT OR REPLACE INTO assets
        (extension, path, mimetype, hash, bytes)
        VALUES (?, ?, ?, ?, ?)"""

        batch = []
        asset_count = 0
        batch_size = 50

        walker = cherrypy.engine.publish(
            "filesystem:walk",
            (".css", ".js", ".svg", ".jinja.html", ".wav")
        ).pop()

        for file_path in walker:
            mime_type, _ = mimetypes.guess_type(file_path.name)

            if not mime_type:
                mime_type = "application/octet-stream"

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
                 (file_path.suffix.lstrip("."),
                  str(file_path),
                  mime_type,
                  file_hash,
                  file_bytes))
            )

            if len(batch) > batch_size:
                self._multi(batch)
                asset_count += len(batch)
                batch = []

        if len(batch) > 0:
            self._multi(batch)
            asset_count += len(batch)
            batch = []