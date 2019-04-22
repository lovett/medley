"""Store arbitrary values in an SQLite database."""

import time
import cherrypy
import msgpack
from . import mixins


class Plugin(cherrypy.process.plugins.SimplePlugin, mixins.Sqlite):
    """A CherryPy plugin for caching arbitrary values to disk."""

    def __init__(self, bus):
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

    def start(self):
        """Define the CherryPy messages to listen for.

        This plugin owns the cdr prefix.
        """

        self.bus.subscribe("cache:get", self.get)
        self.bus.subscribe("cache:match", self.match)
        self.bus.subscribe("cache:set", self.set)
        self.bus.subscribe("cache:clear", self.clear)
        self.bus.subscribe("cache:prune", self.prune)

    def match(self, key_prefix):
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
            "match",
            "{} cache matches for {}".format(len(rows), key_prefix)
        )

        return [row["value"] for row in rows]

    def get(self, key):
        """Retrieve a value from the store by its key."""

        row = self._selectOne(
            """SELECT value as 'value [binary]', created as 'created [datetime]'
            FROM cache
            WHERE key=?
            AND expires > strftime('%s','now')""",
            (key,)
        )

        if "value" in row.keys():
            cherrypy.engine.publish(
                "applog:add",
                "cache",
                "get",
                "hit for {}".format(key)
            )
            return row["value"]

        cherrypy.engine.publish(
            "applog:add",
            "cache",
            "get",
            "miss for {}".format(key)
        )

        return False

    def set(self, key, value, lifespan_seconds=604800):
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

        cherrypy.engine.publish(
            "applog:add",
            "cache",
            "set",
            "cached record for {} for {} seconds".format(
                key, lifespan_seconds
            )
        )
        return True

    def clear(self, key):
        """Remove a value from the store by its key."""
        deletion_count = self._delete("DELETE FROM cache WHERE key=?", (key,))
        cherrypy.engine.publish(
            "applog:add",
            "cache",
            "clear",
            "cleared {} records for {}".format(
                deletion_count,
                key
            )
        )
        return deletion_count

    def prune(self):
        """Delete expired cache entries."""

        deletion_count = self._delete(
            """DELETE FROM cache
            WHERE expires < strftime('%s', 'now')"""
        )

        cherrypy.engine.publish(
            "applog:add",
            "cache",
            "prune",
            "pruned {} records".format(deletion_count)
        )
