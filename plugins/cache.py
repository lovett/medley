"""Store arbitrary values in an SQLite database."""

import sqlite3
import typing
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
            prefix TEXT,
            key TEXT,
            value BLOB,
            expires TEXT,
            created TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE UNIQUE INDEX IF NOT EXISTS index_prefix_and_key
            ON cache(prefix, key);

        CREATE VIEW IF NOT EXISTS unexpired AS
            SELECT prefix, key, value
            FROM cache
            WHERE expires > datetime('now');
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

    @staticmethod
    def keysplit(key: str) -> typing.Tuple[str, str]:
        """Break a key into two parts."""

        if ":" in key:
            return tuple(key.split(":", 1))

        return ("_", key)

    def match(self, prefix: str) -> typing.List[sqlite3.Row]:
        """Retrieve multiple values based on a common prefix."""

        rows = self._select(
            """SELECT value as 'value [binary]'
            FROM unexpired
            WHERE prefix=?""",
            (prefix,)
        )

        cherrypy.engine.publish(
            "applog:add",
            "cache",
            f"match:{prefix}",
            len(rows)
        )

        return [row["value"] for row in rows]

    def get(self, key: str) -> typing.Any:
        """Retrieve a value from the store."""

        prefix, rest = self.keysplit(key)

        return self._selectFirst(
            """SELECT value as 'value [binary]'
            FROM unexpired
            WHERE prefix=? AND key=?""",
            (prefix, rest)
        )

    def set(
            self,
            key: str,
            value: typing.Any,
            lifespan_seconds: int = 604800
    ) -> bool:
        """Add a value to the store."""

        prefix, rest = self.keysplit(key)

        self._execute(
            """INSERT OR REPLACE INTO cache
            (prefix, key, value, expires)
            VALUES (?, ?, ?, datetime('now', ?))""",
            (
                prefix,
                rest,
                msgpack.packb(value, use_bin_type=True),
                f"{lifespan_seconds} seconds"
            )
        )

        return True

    def clear(self, key: str) -> int:
        """Remove a value from the store by its key."""

        prefix, rest = self.keysplit(key)

        deletion_count = self._delete(
            """DELETE FROM cache
            WHERE prefix=? AND key=?""",
            (prefix, rest)
        )

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
            WHERE expires < datetime()"""
        )

        cherrypy.engine.publish(
            "applog:add",
            "cache",
            "prune",
            deletion_count
        )
