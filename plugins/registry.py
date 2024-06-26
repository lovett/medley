"""Key-value storage for app configuration and data."""

from collections import defaultdict
import pathlib
import sqlite3
from typing import Any
from typing import Dict
from typing import Generator
from typing import Iterator
from typing import List
from typing import Optional
from typing import Tuple
from typing import cast
import cherrypy
from plugins import mixins


class Plugin(cherrypy.process.plugins.SimplePlugin, mixins.Sqlite):
    """A key-value style storage resource backed by an SQLite database."""

    def __init__(self, bus: cherrypy.process.wspbus.Bus) -> None:
        cherrypy.process.plugins.SimplePlugin.__init__(self, bus)

        self.db_path = self._path("registry.sqlite")

    def setup(self) -> None:
        """Create the database."""

        self._create("""
        PRAGMA journal_mode=WAL;

        CREATE TABLE IF NOT EXISTS registry (
            key VARCHAR(255) NOT NULL,
            value VARCHAR(255),
            created DEFAULT CURRENT_TIMESTAMP
        );

        """)

        cherrypy.engine.publish("registry:ready")

    def start(self) -> None:
        """Define the CherryPy messages to listen for.

        This plugin owns the registry prefix.
        """

        self.bus.subscribe("server:ready", self.setup)
        self.bus.subscribe("registry:add", self.add)
        self.bus.subscribe("registry:find", self.find)
        self.bus.subscribe("registry:first:key", self.first_key)
        self.bus.subscribe("registry:first:value", self.first_value)
        self.bus.subscribe("registry:keys", self.keys)
        self.bus.subscribe("registry:remove:id", self.remove_id)
        self.bus.subscribe("registry:remove:key", self.remove_key)
        self.bus.subscribe("registry:replace", self.replace)
        self.bus.subscribe("registry:search", self.search)
        self.bus.subscribe("registry:search:dict", self.search_dict)
        self.bus.subscribe("registry:search:multidict", self.search_multidict)
        self.bus.subscribe("registry:search:valuelist", self.search_valuelist)
        self.bus.subscribe("registry:update", self.update)

    def find(self, uid: int) -> Optional[sqlite3.Row]:
        """Select a single record by unique id (sqlite rowid)."""

        return self._selectOne(
            """SELECT rowid, key, value, created as 'created [timestamp]'
            FROM registry
            WHERE rowid=?""",
            (uid,)
        )

    def replace(self, key: str, value: Any) -> None:
        """Create or replace a record.

        Use this when a key should only be associated with a single
        record.

        For multi-record keys, use registry:add instead.

        """

        cherrypy.engine.publish("memorize:clear", key)

        Query = Tuple[str, Tuple[str, ...]]

        queries: Tuple[Query, ...] = (
            ("DELETE FROM registry WHERE key=?",
             (key,)),
        )

        if value:
            queries += (
                ("INSERT INTO registry (key, value) VALUES (?, ?)",
                 (key, value)),
            )

        result = self._multi(queries)

        if result:
            cherrypy.engine.publish("registry:added", key)

    def add(self, key: str, value: Any) -> bool:
        """Create a new record.

        Use this when a key is allowed to be used by multiple records.

        For single-record keys, use registry:replace instead.

        """

        cherrypy.engine.publish("memorize:clear", key)

        result = self._execute(
            "INSERT INTO registry (key, value) VALUES (?, ?)",
            (key, value)
        )

        if result:
            cherrypy.engine.publish("registry:added", key)

        return result

    def search(
            self,
            key: str = "",
            **kwargs: Any
    ) -> Tuple[int, Iterator[sqlite3.Row]]:
        """Search for records by key or value."""

        keys = kwargs.get("keys", ())
        value = kwargs.get("value")
        limit = kwargs.get("limit", 50)
        exact = kwargs.get("exact", False)
        sort_by_value = kwargs.get("sort_by_value", False)
        include_count = kwargs.get("include_count", False)

        params: Tuple[Any, ...] = ()

        sql = """
        SELECT rowid, key, value, unixepoch(created) as created
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
                sql += "AND key = ? "
            else:
                sql += "AND key LIKE ? "

            params = params + (key,)

        if value:
            fuzzy = "*" in value
            value = value.replace("*", "%")

            if fuzzy:
                sql += "AND VALUE LIKE ? "
            else:
                sql += "AND value=? "

            params = params + (value,)

        if sort_by_value:
            sql += "ORDER BY value COLLATE NOCASE "
        else:
            sql += "ORDER BY key COLLATE NOCASE "

        if limit > 0:
            sql += f" LIMIT {limit}"

        result = cast(
            Any,
            self._select_generator(sql, params)
        )

        if include_count:
            count = self._count(sql, params)
            return (count, result)

        return (-1, result)

    def search_dict(
            self,
            *args: Any,
            **kwargs: Any
    ) -> Dict[str, Any]:
        """Shape a search result as a key-value dict."""

        key_slice = kwargs.get("key_slice", 0)

        _, rows = self.search(*args, **kwargs)

        return {
            row["key"].split(":", key_slice).pop():
            row["value"]
            for row in rows
        }

    def search_multidict(
            self,
            *args: Any,
            **kwargs: Any
    ) -> Dict[str, List]:
        """Shape a search result as a dict whose values are lists."""

        key_slice = kwargs.get("key_slice", 0)

        _, rows = self.search(*args, **kwargs)

        multi_dict: Dict[str, List] = defaultdict(list)

        for row in rows:
            key = row["key"].split(":", key_slice).pop()
            multi_dict[key].append(row["value"])

        return multi_dict

    def search_valuelist(
            self,
            *args: Any,
            **kwargs: Any
    ) -> List:
        """Shape a result set as a list of values."""

        _, rows = self.search(*args, **kwargs)

        return [row["value"] for row in rows]

    def remove_key(self, key: str) -> int:
        """Delete any records for a key."""

        cherrypy.engine.publish("memorize:clear", key)
        deletions = self._delete("DELETE FROM registry WHERE key=?", (key,))

        cherrypy.engine.publish("registry:removed", key)

        return deletions

    def remove_id(self, uid: int) -> None:
        """Delete a record by unique id (sqlite rowid)."""

        row = self.find(uid)

        if not row:
            return

        deletions = self._delete(
            "DELETE FROM registry WHERE rowid=?",
            (uid,)
        )

        if deletions > 0:
            cherrypy.engine.publish("registry:removed", row["key"])

    def first_key(
            self,
            value: Any = None,
            key_prefix: str = ""
    ) -> Optional[str]:
        """Perform a search by value and return the key of the first match.

        For cases where the value may be associated with more than one
        key, the key_prefix argument provides additional specificity.

        """
        _, rows = self.search(key=key_prefix, value=value, limit=1)

        try:
            return cast(str, next(rows)["key"])
        except StopIteration:
            return None

    def first_value(
            self,
            key: str,
            memorize: bool = False,
            as_path: bool = False,
            default: Any = None
    ) -> Any:
        """Perform a search by key and return the value of the first match."""

        if memorize:
            memorize_hit, memorize_value = cherrypy.engine.publish(
                "memorize:get",
                key
            ).pop()

            if memorize_hit:
                return memorize_value

        _, rows = self.search(key=key, exact=True, limit=1)

        try:
            result = next(rows)
            value = result["value"]
        except StopIteration:
            value = default

        if as_path:
            value = pathlib.Path(value)

        if memorize:
            cherrypy.engine.publish("memorize:set", key, value)

        return value

    def keys(
            self,
            depth: int = 1
    ) -> Generator[Any, None, None]:
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
        ORDER BY val COLLATE NOCASE
        """

        result = self._select(sql, [depth])

        return (row["val"] for row in result)

    def update(self, rowid: int, key: str, value: Any) -> bool:
        """Modify an existing record."""

        cherrypy.engine.publish("memorize:clear", key)

        self._execute(
            "UPDATE registry SET key=?, value=? WHERE rowid=?",
            (key, value, rowid)
        )

        cherrypy.engine.publish("registry:updated", key)

        return True
