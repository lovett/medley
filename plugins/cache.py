"""Store arbitrary values in an SQLite database."""

import json
import typing
import cherrypy
from . import mixins


class Plugin(cherrypy.process.plugins.SimplePlugin, mixins.Sqlite):
    """A CherryPy plugin for caching arbitrary values to disk."""

    def __init__(self, bus: cherrypy.process.wspbus.Bus) -> None:
        cherrypy.process.plugins.SimplePlugin.__init__(self, bus)

        self.db_path = self._path("cache.sqlite")

    def setup(self) -> None:
        """Create the database."""

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

        self.bus.subscribe("server:ready", self.setup)
        self.bus.subscribe("cache:get", self.get)
        self.bus.subscribe("cache:match", self.match)
        self.bus.subscribe("cache:set", self.set)
        self.bus.subscribe("cache:clear", self.clear)
        self.bus.subscribe("cache:prune", self.prune)

    @staticmethod
    def keysplit(key: str) -> typing.Tuple[str, str]:
        """Break a key into two parts."""

        if ":" in key:
            return typing.cast(
                typing.Tuple[str, str],
                tuple(key.split(":", 1))
            )

        return ("_", key)

    def match(self, prefix: str) -> typing.Iterator[typing.Any]:
        """Retrieve multiple values based on a common prefix."""

        rows = self._select_generator(
            """SELECT value
            FROM unexpired
            WHERE prefix=?""",
            (prefix,)
        )

        for row in rows:
            if not isinstance(row["value"], str):
                yield row["value"]
                continue
            try:
                yield json.loads(row["value"])
            except json.decoder.JSONDecodeError:
                pass

    def get(self, key: str) -> typing.Any:
        """Retrieve a value from the store."""

        prefix, rest = self.keysplit(key)

        value = self._selectFirst(
            """SELECT value
            FROM unexpired
            WHERE prefix=? AND key=?""",
            (prefix, rest)
        )

        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.decoder.JSONDecodeError:
                pass

        return value

    def set(
            self,
            key: str,
            value: typing.Any,
            lifespan_seconds: int = 604800
    ) -> bool:
        """Add a value to the store.

        If the value is anything other than bytes or a string, JSON
        encoding will be attempted. If the value cannot be JSON
        encoded, no caching will occur.

        """

        value_for_storage = value

        if isinstance(value, (dict, list, set)):
            try:
                value_for_storage = json.dumps(value)
            except TypeError:
                cherrypy.engine.publish(
                    "applog:add",
                    "cache:set",
                    f"A value for {key} could not be cached."
                )

                return False

        prefix, rest = self.keysplit(key)

        self._execute(
            """INSERT OR REPLACE INTO cache
            (prefix, key, value, expires)
            VALUES (?, ?, ?, datetime('now', ?))""",
            (
                prefix,
                rest,
                value_for_storage,
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

        unit = "row" if deletion_count == 1 else "rows"

        cherrypy.engine.publish(
            "applog:add",
            "cache:clear",
            f"{deletion_count} {unit} deleted"
        )

        return deletion_count

    def prune(self) -> None:
        """Delete expired cache entries."""

        deletion_count = self._delete(
            """DELETE FROM cache
            WHERE expires < datetime()"""
        )

        unit = "row" if deletion_count == 1 else "rows"

        cherrypy.engine.publish(
            "applog:add",
            "cache:prune",
            f"{deletion_count} {unit} deleted"
        )
