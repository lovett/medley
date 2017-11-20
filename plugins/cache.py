import cherrypy
import time
import msgpack
from . import mixins

class Plugin(cherrypy.process.plugins.SimplePlugin, mixins.Sqlite):

    def __init__(self, bus):
        cherrypy.process.plugins.SimplePlugin.__init__(self, bus)

        self.db_path = self._path("cache.sqlite")

        self._create("""CREATE TABLE IF NOT EXISTS cache (
            key UNIQUE NOT NULL,
            value, expires,
            created DEFAULT CURRENT_TIMESTAMP
            )""")

    def start(self):
        self.bus.subscribe("cache:get", self.get)
        self.bus.subscribe("cache:set", self.set)
        self.bus.subscribe("cache:clear", self.clear)

    def stop(self):
        pass

    def get(self, key):
        """Retrieve a value from the cache by its key"""

        self.prune(key)

        row = self._selectOne("SELECT value as 'value [binary]', created as 'created [created]' FROM cache WHERE key=?", (key,))

        if "value" in row.keys():
            cherrypy.engine.publish("app-log", "cache", "hit", key)
            return row["value"]

        cherrypy.engine.publish("app-log", "cache", "miss", key)
        return False

    def set(self, key, value, lifespan_seconds=3600):
        expires = time.time() + int(lifespan_seconds)
        packed_value = msgpack.packb(value, use_bin_type=True)
        self._insert(
            "INSERT OR REPLACE INTO cache (key, value, expires) VALUES (?, ?, ?)",
            [(key, packed_value, expires)]
        )
        return True

    def clear(self, key):
        deletions = self._delete("DELETE FROM cache WHERE key=?", (key,))
        cherrypy.engine.publish("app-log", "cache", "clear:{}".format(key), deletions)
        return deletions

    def prune(self, key):
        """Delete expired cache entries by key"""
        deletions = self._delete("DELETE FROM cache WHERE key=? AND expires < ?", (key, time.time()))
        cherrypy.engine.publish("app-log", "cache", "prune:{}".format(key), deletions)
