"""Key-value storage for app configuration and data."""

from collections import defaultdict, OrderedDict
import cherrypy
import pendulum
from . import mixins


class Plugin(cherrypy.process.plugins.SimplePlugin, mixins.Sqlite):
    """A key-value style storage resource backed by an SQLite database."""

    def __init__(self, bus):
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

    def start(self):
        """Define the CherryPy messages to listen for.

        This plugin owns the registry prefix.
        """

        self.bus.subscribe("registry:remove", self.remove)
        self.bus.subscribe("registry:remove_id", self.remove_id)
        self.bus.subscribe("registry:find_id", self.find)
        self.bus.subscribe("registry:first_key", self.first_key)
        self.bus.subscribe("registry:first_value", self.first_value)
        self.bus.subscribe("registry:distinct_keys", self.distinct_keys)
        self.bus.subscribe("registry:list_keys", self.list_keys)
        self.bus.subscribe("registry:add", self.add)
        self.bus.subscribe("registry:search", self.search)
        self.bus.subscribe("registry:local_timezone", self.local_timezone)

    def find(self, uid):
        """Select a single record by unique id (sqlite rowid)."""

        return self._selectOne(
            """SELECT rowid, key, value, created as 'created [datetime]'
            FROM registry
            WHERE rowid=?""",
            (uid,)
        )

    def add(self, key, values=(), replace=False):
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
            self.remove(key)

        return self._insert(
            "INSERT INTO registry (key, value) VALUES (?, ?)",
            [(key, value) for value in clean_values]
        )

    # pylint: disable=too-many-arguments
    # pylint: disable=too-many-locals
    # pylint: disable=too-many-branches
    def search(self, key=None, keys=(), value=None, limit=100, exact=False,
               as_dict=False, as_value_list=False, as_multivalue_dict=False,
               key_slice=0, sorted_by_key=False):
        """Search for records by key or value."""

        params = []

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
                key = "%{}%".format(key)

            if exact:
                sql += "AND key = ?"
            else:
                sql += "AND key LIKE ? "

            params.append(key)

        if value:
            fuzzy = "*" in value
            value = value.replace("*", "%")

            if fuzzy:
                sql += "AND VALUE LIKE ?"
            else:
                sql += "AND value=?"

            params.append(value)

        if sorted_by_key:
            sql += "ORDER BY key"
        else:
            sql += " ORDER BY rowid DESC"

        sql += " LIMIT {}".format(limit)

        result = self._select(sql, params)

        if as_dict:
            result = {
                row["key"].split(":", key_slice).pop():
                row["value"]
                for row in result
            }

            # Go the extra mile for Python 3.5.
            result = OrderedDict(sorted(
                result.items(),
                key=lambda t: t[0]
            ))

        if as_multivalue_dict:
            multi_dict = defaultdict(list)

            for row in result:
                k = row["key"]
                if key_slice > 0:
                    sliced_key = k.split(":")[key_slice:]
                    k = ":".join(sliced_key)
                multi_dict[k].append(row["value"])
            result = multi_dict

        if as_value_list:
            result = [row["value"] for row in result]

        return result

    def remove(self, key):
        """Delete any records for a key."""

        cherrypy.engine.publish("memorize:clear", key)
        deletions = self._delete("DELETE FROM registry WHERE key=?", (key,))
        cherrypy.engine.publish(
            "applog:add",
            "registry",
            "remove_key:{}".format(key),
            deletions
        )

        return deletions

    def remove_id(self, rowid):
        """Delete a record by unique id (sqlite rowid)."""

        deletions = self._delete(
            "DELETE FROM registry WHERE rowid=?",
            (rowid,)
        )
        cherrypy.engine.publish(
            "applog:add",
            "registry",
            "remove_id:{}".format(rowid),
            deletions
        )

        return deletions

    def first_key(self, value=None, key_prefix=None):
        """Perform a search by value and return the key of the first match.

        For cases where the value may be associated with more than one
        key, the key_prefix argument provides additional specificity.

        """
        result = self.search(key=key_prefix, value=value, limit=1)

        if not result:
            return None

        return result[0]["key"]

    def first_value(self, key, memorize=False):
        """Perform a search by key and return the value of the first match."""

        if memorize:
            memorize_hit, memorize_value = cherrypy.engine.publish(
                "memorize:get",
                key
            ).pop()

            if memorize_hit:
                return memorize_value

        result = self.search(key=key, limit=1)

        try:
            value = result[0]["value"]
        except IndexError:
            value = None

        if memorize:
            cherrypy.engine.publish("memorize:set", key, value)
        return value

    def distinct_keys(self, key, strip_prefix=True):
        """Find all keys that share a common prefix."""

        sql = "SELECT distinct key FROM registry WHERE (1) AND key LIKE ?"

        key = key.replace("*", "%")

        rows = self._select(sql, [key])

        keys = [row["key"] for row in rows]

        if strip_prefix:
            return [key.split(":", 1).pop() for key in keys]

        return keys

    def local_timezone(self):
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

        return timezone

    def list_keys(self, depth=1):
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
