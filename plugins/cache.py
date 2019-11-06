"""Store arbitrary values in an SQLite database."""

import sqlite3
import time
from typing import List, Any
import cherrypy
import msgpack
from . import mixins


class Plugin(cherrypy.process.plugins.SimplePlugin, mixins.Sqlite):
    """A CherryPy plugin for caching arbitrary values to disk."""

    def __init__(self, bus: cherrypy.process.wspbus.Bus) -> None:
        cherrypy.process.plugins.SimplePlugin.__init__(self, bus)

        self.db_path = self._path("cache.sqlite")

        self._create("""
        PRAGMA journal_mode=WAL;

        CREATE TABLE IF NOT EXISTS cache (
            key UNIQUE NOT NULL,
            value TEXT,
            expires REAL,
            created DEFAULT CURRENT_TIMESTAMP
        );

        """)

    def start(self) -> None:
        """Define the CherryPy messages to listen for.

        This plugin owns the cdr prefix.
        """

        self.bus.subscribe("cache:get", self.get)
        self.bus.subscribe("cache:match", self.match)
        self.bus.subscribe("cache:set", self.set)
        self.bus.subscribe("cache:clear", self.clear)
        self.bus.subscribe("cache:prune", self.prune)

    def match(self, key_prefix: str) -> List[sqlite3.Row]:
        """Retrieve multiple keys based on a common prefix."""

        rows = self._select(
            """SELECT value as 'value [binary]', created as 'created [datetime]'
            FROM cache
            WHERE key LIKE ?
            AND expires > strftime('%s','now')""",
            (key_prefix + "%",)
        )

        cherrypy.engine.publish(
            "applog:add",
            "cache",
            f"match:{key_prefix}",
            len(rows)
        )

        return [row["value"] for row in rows]

    def get(self, key: str) -> Any:
        """Retrieve a value from the store by its key."""

        return self._selectFirst(
            """SELECT value as 'value [binary]'
            FROM cache
            WHERE key=?
            AND expires > strftime('%s','now')""",
            (key,)
        )

    def set(self,
            key: str,
            value: Any,
            lifespan_seconds: int = 604800) -> bool:
        """Add a value to the store.

        The default lifespan for a cache entry is 1 week."""

        expires = time.time() + int(lifespan_seconds)
        packed_value = msgpack.packb(value, use_bin_type=True)
        self._insert(
            """INSERT OR REPLACE INTO cache
            (key, value, expires)
            VALUES (?, ?, ?)""",
            [(key, packed_value, expires)]
        )

        return True

    def clear(self, key: str) -> int:
        """Remove a value from the store by its key."""
        deletion_count = self._delete("DELETE FROM cache WHERE key=?", (key,))
        cherrypy.engine.publish(
            "applog:add",
            "cache",
            f"clear:{key}",
            deletion_count
        )
        return deletion_count

    def prune(self) -> None:
        """Delete expired cache entries."""

        deletion_count = self._delete(
            """DELETE FROM cache
            WHERE expires < strftime('%s', 'now')"""
        )

        cherrypy.engine.publish(
            "applog:add",
            "cache",
            "prune",
            deletion_count
        )
