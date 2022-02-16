"""Store arbitrary files in SQLite."""

import sqlite3
from typing import Iterator
from typing import Optional
from typing import cast
from pathlib import Path
import cherrypy
from plugins import mixins


class Plugin(cherrypy.process.plugins.SimplePlugin, mixins.Sqlite):
    """A CherryPy plugin for storing files in an SQLite database."""

    def __init__(self, bus: cherrypy.process.wspbus.Bus) -> None:
        cherrypy.process.plugins.SimplePlugin.__init__(self, bus)

        self.db_path = self._path("warehouse.sqlite")

        self._create("""
        PRAGMA journal_mode=WAL;
        PRAGMA foreign_keys=ON;

        CREATE TABLE IF NOT EXISTS warehouse (
            created DEFAULT CURRENT_TIMESTAMP,
            path TEXT,
            content_type TEXT,
            chunk BLOB
        );

        CREATE INDEX IF NOT EXISTS index_path
            ON warehouse(path);

        """)

    def start(self) -> None:
        """Define the CherryPy messages to listen for.

        This plugin owns the warehouse prefix.

        """

        self.bus.subscribe("warehouse:add:chunk", self.add_chunk)
        self.bus.subscribe("warehouse:remove", self.remove_file)
        self.bus.subscribe("warehouse:get:chunks", self.get_chunk)
        self.bus.subscribe("warehouse:get:type", self.get_type)
        self.bus.subscribe("warehouse:list", self.list_files)

    def add_chunk(
            self,
            path: Path,
            content_type: str,
            chunk: bytes
    ) -> None:
        """Store a file."""

        self._execute(
            """INSERT INTO warehouse
            (path, content_type, chunk)
            VALUES (?, ?, ?)""",
            (path.as_posix(), content_type, chunk)
        )

    def get_type(self, path: Path) -> Optional[str]:
        """Retrieve the content type of a stored file."""

        return cast(
            str,
            self._selectFirst(
                """SELECT content_type
                FROM warehouse
                WHERE path=?
                LIMIT 1""",
                (path.as_posix(),)
            )
        )

    def get_chunk(self, path: Path) -> Iterator[bytes]:
        """Retrieve a previously-stored file."""

        rows = self._select_generator(
            """SELECT chunk
            FROM warehouse
            WHERE path=?
            ORDER BY rowid""",
            (path.as_posix(),)
        )

        for row in rows:
            yield row["chunk"]

    def remove_file(self, path: Path) -> None:
        """Delete a previously-stored file."""

        self._execute(
            "DELETE FROM warehouse WHERE path=?",
            (path.as_posix(),)
        )

    def list_files(self) -> Iterator[sqlite3.Row]:
        """List available files by path."""

        return self._select_generator(
            """SELECT path as 'path [url]', content_type,
            created as 'created [local_datetime]',
            SUM(LENGTH(chunk)) as total_bytes
            FROM warehouse
            GROUP BY path
            ORDER BY path"""
        )
