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

        self._create("""CREATE TABLE IF NOT EXISTS cache (
            key UNIQUE NOT NULL,
            value, expires,
            created DEFAULT CURRENT_TIMESTAMP
            )""")

    def start(self):
        """Define the CherryPy messages to listen for.

        This plugin owns the cdr prefix.
        """

        self.bus.subscribe("cache:get", self.get)
        self.bus.subscribe("cache:match", self.match)
        self.bus.subscribe("cache:set", self.set)
        self.bus.subscribe("cache:clear", self.clear)

    def match(self, key_prefix):
        """Retrieve multiple keys based on a common prefix."""

        rows = self._select(
            """SELECT value as 'value [binary]', created as 'created [datetime]'
            FROM cache
            WHERE key LIKE ?
            AND expires < strftime('%s','now')""",
            (key_prefix + "%",)
        )

        if not rows:
            cherrypy.engine.publish("applog:add", "cache", "miss", key_prefix)
            return ()

        cherrypy.engine.publish("applog:add", "cache", "hit", key_prefix)

        return [row["value"] for row in rows]

    def get(self, key):
        """Retrieve a value from the store by its key."""

        row = self._selectOne(
            """SELECT value as 'value [binary]', created as 'created [datetime]'
            FROM cache
            WHERE key=?
            AND expires < strftime('%s','now')""",
            (key,)
        )

        if "value" in row.keys():
            cherrypy.engine.publish("applog:add", "cache", "hit", key)
            return row["value"]

        cherrypy.engine.publish("applog:add", "cache", "miss", key)
        return False

    def set(self, key, value, lifespan_seconds=3600):
        """Add a value to the store."""

        expires = time.time() + int(lifespan_seconds)
        packed_value = msgpack.packb(value, use_bin_type=True)
        self._insert(
            """INSERT OR REPLACE INTO cache
            (key, value, expires)
            VALUES (?, ?, ?)""",
            [(key, packed_value, expires)]
        )
        return True

    def clear(self, key):
        """Remove a value from the store by its key."""
        deletions = self._delete("DELETE FROM cache WHERE key=?", (key,))
        cherrypy.engine.publish(
            "applog:add",
            "cache",
            "clear:{}".format(key),
            deletions
        )
        return deletions

    def prune(self, key):
        """Delete expired cache entries by key."""

        deletions = self._delete(
            "DELETE FROM cache WHERE key=? AND expires < ?",
            (key, time.time())
        )
        cherrypy.engine.publish(
            "applog:add",
            "cache",
            "prune:{}".format(key),
            deletions
        )
