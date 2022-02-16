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

        self.bus.subscribe("assets:publish", self.publish)

        if cherrypy.config.get("zipapp"):
            self.bus.subscribe("assets:get", self.asset_from_db)
            self.bus.subscribe("assets:hash", self.hash_from_db)
        else:
            self.bus.subscribe("assets:get", self.asset_from_fs)
            self.bus.subscribe("assets:hash", self.hash_from_fs)

    def hash_from_db(self, target: Path) -> str:
        """Retrieve a published asset's hash."""

        asset_hash = cast(str, self._selectFirst(
            "SELECT hash FROM assets WHERE extension=? AND path=?",
            (target.suffix.lstrip("."), str(target),)
        ))

        return asset_hash or ""

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

    def asset_from_db(self, target: Path) -> Tuple[bytes, str]:
        """Retrieve a published asset and its mimetype."""

        row = self._selectOne(
            "SELECT bytes, mimetype FROM assets WHERE extension=? AND path=?",
            (target.suffix.lstrip("."), str(target))
        )

        if not row:
            return (b"", "")

        return (
            cast(bytes, row["bytes"]),
            cast(str, row["mimetype"])
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

    def publish(self, reset: bool = False) -> None:
        """Export assets to a database.

        When the application runs as a zipapp, asset access can be
        excessively slow due to the IO needed to read the zip file,
        especially when trying to serve multiple requests at the same
        time (it's normal for a page to reference multiple assets).

        On the other hand, bundling assets in the zip is very
        convenient for deployment.

        By copying assets to SQLite, the IO issue is mitigated and the
        deployment advantage is preserved.

        The reset parameter controls publishing frequency. If true,
        assets will be published regardless of whether the database is
        currently populated. This is useful for the --publish CLI
        argument. If false, assets will only be published if the
        database is empty. This is useful when the application is
        starting up for the first time.

        """

        asset_count = self._selectFirst("SELECT count(*) FROM assets")

        if reset is False and asset_count > 0:
            cherrypy.log("Assets already published.")
            return

        cherrypy.log("Publishing assets...")
        self._execute("DELETE FROM assets")

        insert_sql = """INSERT OR REPLACE INTO assets
        (extension, path, mimetype, hash, bytes)
        VALUES (?, ?, ?, ?, ?)"""

        batch = []
        asset_count = 0
        batch_size = 50

        walker = cherrypy.engine.publish(
            "filesystem:walk",
            (".css", ".min.css", ".js", ".svg", ".jinja.html", ".wav")
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

        label = "assets"
        if asset_count == 1:
            label = "asset"

        cherrypy.log(f"{asset_count} {label} published.")
