import cherrypy
from . import mixins
from collections import defaultdict
import pendulum


class Plugin(cherrypy.process.plugins.SimplePlugin, mixins.Sqlite):


    def __init__(self, bus):
        cherrypy.process.plugins.SimplePlugin.__init__(self, bus)

        self.db_path = self._path("registry.sqlite")

        self._create("""CREATE TABLE IF NOT EXISTS registry (
            key VARCHAR(255) NOT NULL,
            value VARCHAR(255),
            created DEFAULT CURRENT_TIMESTAMP)""")

    def start(self):
        self.bus.subscribe("registry:remove", self.remove)
        self.bus.subscribe("registry:remove_id", self.removeId)
        self.bus.subscribe("registry:find_id", self.find)
        self.bus.subscribe("registry:first_key", self.firstKey)
        self.bus.subscribe("registry:first_value", self.firstValue)
        self.bus.subscribe("registry:distinct_keys", self.distinctKeys)
        self.bus.subscribe("registry:add", self.add)
        self.bus.subscribe("registry:search", self.search)
        self.bus.subscribe("registry:local_timezone", self.local_timezone)

    def stop(self):
        pass

    def find(self, uid):
        return self._selectOne(
            "SELECT rowid, key, value, created as 'created [datetime]' FROM registry WHERE rowid=?",
            (uid,)
        )

    def add(self, key, values=[], replace=False):
        cherrypy.engine.publish("memorize:clear", key)
        if replace:
            self.remove(key)

        return self._insert(
            "INSERT INTO registry (key, value) VALUES (?, ?)",
             [(key, value) for value in values]
        )

    def search(self, key=None, keys=[], value=None, limit=100, exact=False, as_dict=False, as_value_list=False, as_multivalue_dict=False, key_slice=0):
        params = []

        sql = "SELECT rowid, key, value, created as 'created [datetime]' FROM registry WHERE (1) "

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

        sql += " ORDER BY rowid DESC"
        sql += " LIMIT {}".format(limit)

        result = self._select(sql, params)

        if as_dict:
            result = {
                row["key"].split(":", key_slice).pop():
                row["value"]
                for row in result
            }

        if as_multivalue_dict:
            d = defaultdict(list)

            for row in result:
                k = row["key"]
                if key_slice > 0:
                    sliced_key = k.split(":")[key_slice:]
                    k = ":".join(sliced_key)
                d[k].append(row["value"])
            result = d

        if as_value_list:
            result = [row["value"] for row in result]

        return result

    def remove(self, key):
        cherrypy.engine.publish("memorize:clear", key)
        deletions = self._delete("DELETE FROM registry WHERE key=?", (key,))
        cherrypy.engine.publish("applog:add", "registry", "remove_key:{}".format(key), deletions)
        return deletions

    def removeId(self, rowid):
        deletions = self._delete("DELETE FROM registry WHERE rowid=?", (rowid,))
        cherrypy.engine.publish("applog:add", "registry", "remove_id:{}".format(rowid), deletions)
        return deletions

    def firstKey(self, value=None):
        result = self.search(value=value, limit=1)

        if not result:
            return None

        return result[0]["key"]

    def firstValue(self, key, memorize=False):
        if memorize:
            memorize_hit, memorize_value = cherrypy.engine.publish("memorize:get", key).pop()
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

    def distinctKeys(self, key, value=None, stripPrefix=True):
        sql = "SELECT distinct key FROM registry WHERE (1) AND key LIKE ?"

        key = key.replace("*", "%")

        rows = self._select(sql, [key])

        keys = [row["key"] for row in rows]

        if stripPrefix:
            return [key.split(":", 1).pop() for key in keys]

        return keys

    def local_timezone(self):
        """Determine the timezone of the application.

        The registry is checked first so that the application timezone
        can be independent of the server's timezone. But the server's
        timezone also acts as a fallback.

        """

        timezone = self.firstValue(
            "config:timezone",
            memorize=True
        )

        if not timezone:
            timezone = pendulum.now().timezone.name

        return timezone
