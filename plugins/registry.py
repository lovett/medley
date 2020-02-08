"""Key-value storage for app configuration and data."""

from collections import defaultdict
import pathlib
import sqlite3
import typing
import cherrypy
import pendulum
from . import mixins


class Plugin(cherrypy.process.plugins.SimplePlugin, mixins.Sqlite):
    """A key-value style storage resource backed by an SQLite database."""

    def __init__(self, bus: cherrypy.process.wspbus.Bus) -> None:
        cherrypy.process.plugins.SimplePlugin.__init__(self, bus)

        self.db_path = self._path("registry.sqlite")

        self._create("""
        PRAGMA journal_mode=WAL;

        CREATE TABLE IF NOT EXISTS registry (
            key VARCHAR(255) NOT NULL,
            value VARCHAR(255),
            created DEFAULT CURRENT_TIMESTAMP
        );

        """)

    def start(self) -> None:
        """Define the CherryPy messages to listen for.

        This plugin owns the registry prefix.
        """

        self.bus.subscribe("registry:add", self.add)
        self.bus.subscribe("registry:find", self.find)
        self.bus.subscribe("registry:find:key", self.find_key)
        self.bus.subscribe("registry:first:key", self.first_key)
        self.bus.subscribe("registry:first:value", self.first_value)
        self.bus.subscribe("registry:keys", self.keys)
        self.bus.subscribe("registry:timezone", self.timezone)
        self.bus.subscribe("registry:remove:id", self.remove_id)
        self.bus.subscribe("registry:remove:key", self.remove_key)
        self.bus.subscribe("registry:search", self.search)
        self.bus.subscribe("registry:search:dict", self.search_dict)
        self.bus.subscribe("registry:search:multidict", self.search_multidict)
        self.bus.subscribe("registry:search:valuelist", self.search_valuelist)

    def find(self, uid: str) -> typing.Optional[sqlite3.Row]:
        """Select a single record by unique id (sqlite rowid)."""

        return self._selectOne(
            """SELECT rowid, key, value, created as 'created [datetime]'
            FROM registry
            WHERE rowid=?""",
            (uid,)
        )

    def find_key(self, key: str) -> typing.Optional[sqlite3.Row]:
        """Select a single record by its key."""

        return self._selectOne(
            """SELECT rowid, key, value, created as 'created [datetime]'
            FROM registry
            WHERE key=?""",
            (key,)
        )

    def add(
            self,
            key: str,
            values: typing.Iterable[typing.Any],
            replace: bool = False
    ) -> bool:
        """Add one or more values for the given key, optionally deleting any
        existing values.

        CRLF newlines will be converted to Unix-style LF to make
        things easier for apps that use multi-line values.

        """

        clean_values = [
            value.replace("\r", "")
            for value in values
        ]

        cherrypy.engine.publish("memorize:clear", key)
        if replace:
            self.remove_key(key)

        return self._insert(
            "INSERT INTO registry (key, value) VALUES (?, ?)",
            [(key, value) for value in clean_values]
        )

    def search(
            self,
            key: str = "",
            **kwargs: typing.Any
    ) -> typing.Any:
        """Search for records by key or value."""

        keys = kwargs.get("keys", ())
        value = kwargs.get("value")
        limit = kwargs.get("limit", 25)
        exact = kwargs.get("exact", False)
        include_count = kwargs.get("include_count", False)

        params: typing.Tuple[typing.Any, ...] = ()

        sql = """
        SELECT rowid, key, value, created as 'created [datetime]'
        FROM registry
        WHERE (1) """

        if keys:
            sql += "AND key IN ("
            sql += ", ".join("?" * len(keys))
            sql += ") "
            params = keys
        elif key:
            fuzzy = "*" in key

            if fuzzy:
                key = key.replace("*", "%")
            elif not exact:
                key = f"%{key}%"

            if exact:
                sql += "AND key = ?"
            else:
                sql += "AND key LIKE ? "

            params = params + (key,)

        if value:
            fuzzy = "*" in value
            value = value.replace("*", "%")

            if fuzzy:
                sql += "AND VALUE LIKE ?"
            else:
                sql += "AND value=?"

            params = params + (value,)

        sql += f"ORDER BY key LIMIT {limit}"

        result = typing.cast(
            typing.Any,
            self._select(sql, params)
        )

        if include_count:
            count = self._count(sql, params)
            return (count, result)

        return result

    def search_dict(
            self,
            *args: typing.Any,
            **kwargs: typing.Any
    ) -> typing.Dict[str, typing.Any]:
        """Shape a search result as a key-value dict."""

        key_slice = kwargs.get("key_slice", 0)

        rows = self.search(*args, **kwargs)

        return {
            row["key"].split(":", key_slice).pop():
            row["value"]
            for row in rows
        }

    def search_multidict(
            self,
            *args: typing.Any,
            **kwargs: typing.Any
    ) -> typing.Dict[str, typing.List]:
        """Shape a search result as a dict whose values are lists."""

        key_slice = kwargs.get("key_slice", 0)

        rows = self.search(*args, **kwargs)

        multi_dict: typing.Dict[str, typing.List] = defaultdict(list)

        for row in rows:
            key = row["key"].split(":", key_slice).pop()
            multi_dict[key].append(row["value"])

        return multi_dict

    def search_valuelist(
            self,
            *args: typing.Any,
            **kwargs: typing.Any
    ) -> typing.List:
        """Shape a result set as a list of values."""

        rows = self.search(*args, **kwargs)

        return [row["value"] for row in rows]

    def remove_key(self, key: str) -> int:
        """Delete any records for a key."""

        cherrypy.engine.publish("memorize:clear", key)
        deletions = self._delete("DELETE FROM registry WHERE key=?", (key,))

        return deletions

    def remove_id(self, rowid: int) -> int:
        """Delete a record by unique id (sqlite rowid)."""

        deletions = self._delete(
            "DELETE FROM registry WHERE rowid=?",
            (rowid,)
        )

        return deletions

    def first_key(
            self,
            value: typing.Any = None,
            key_prefix: str = ""
    ) -> typing.Optional[str]:
        """Perform a search by value and return the key of the first match.

        For cases where the value may be associated with more than one
        key, the key_prefix argument provides additional specificity.

        """
        result = self.search(key=key_prefix, value=value, limit=1)

        if not result:
            return None

        return typing.cast(str, result[0]["key"])

    def first_value(
            self,
            key: str,
            memorize: bool = False,
            as_path: bool = False,
            default: typing.Any = None
    ) -> typing.Any:
        """Perform a search by key and return the value of the first match."""

        if memorize:
            memorize_hit, memorize_value = cherrypy.engine.publish(
                "memorize:get",
                key
            ).pop()

            if memorize_hit:
                return memorize_value

        result = self.search(key=key, exact=True, limit=1)

        try:
            value = result[0]["value"]
        except IndexError:
            value = default

        if as_path:
            value = pathlib.Path(value)

        if memorize:
            cherrypy.engine.publish("memorize:set", key, value)

        return value

    def timezone(self) -> str:
        """Determine the timezone of the application.

        The registry is checked first so that the application timezone
        can be independent of the server's timezone. But the server's
        timezone also acts as a fallback.

        """

        timezone = self.first_value(
            "config:timezone",
            memorize=True
        )

        if not timezone:
            timezone = pendulum.now().timezone.name

        return typing.cast(str, timezone)

    def keys(
            self,
            depth: int = 1
    ) -> typing.Generator[typing.Any, None, None]:
        """List known keys filtered by the number of segments.

        Returns a generator that yields key names.
        """

        sql = """
        WITH RECURSIVE cte(val, rest, depth) AS (
          SELECT '', key, 0 FROM registry
          UNION ALL
          SELECT
            CASE
              WHEN instr(rest, ':') > 0
                THEN val || substr(rest, 1, instr(rest, ':'))
              ELSE
                val || rest
            END,
            CASE
              WHEN instr(rest, ':') > 0
                THEN substr(rest, instr(rest, ':') + 1)
              ELSE
                NULL
            END,
            depth + 1
          FROM cte
          WHERE rest is not null
        )
        SELECT DISTINCT rtrim(val, ':') AS val
        FROM cte
        WHERE depth=?
        ORDER BY val
        """

        result = self._select(sql, [depth])

        return (row["val"] for row in result)
