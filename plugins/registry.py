import cherrypy
from . import mixins

class Plugin(cherrypy.process.plugins.SimplePlugin, mixins.Sqlite):

    def __init__(self, bus):
        cherrypy.process.plugins.SimplePlugin.__init__(self, bus)

        self.db_path = self._path("registry.sqlite")

        self._registerConverters()

        self._create("""CREATE TABLE IF NOT EXISTS registry (
            key VARCHAR(255) NOT NULL,
            value VARCHAR(255),
            created DEFAULT CURRENT_TIMESTAMP)""")

    def start(self):
        self.bus.subscribe("registry:remove", self.remove)
        self.bus.subscribe("registry:first_key", self.firstKey)
        self.bus.subscribe("registry:distinct_keys", self.distinctKeys)
        self.bus.subscribe("registry:add", self.add)
        self.bus.subscribe("registry:search", self.search)

    def stop(self):
        pass

    def add(self, key, values=[], replace=False):
        if replace:
            self.remove(key)

        return self._insert(
            "INSERT INTO registry (key, value) VALUES (?, ?)",
             [(key, value) for value in values]
        )

    def search(self, key=None, keys=[], value=None, limit=100, exact=False, as_dict=False, as_value_list=False):
        params = []

        sql = "SELECT rowid, key, value, created as 'created [created]' FROM registry WHERE (1) "

        if len(keys) > 0:
            sql += "AND key IN ("
            sql += ", ".join("?" * len(keys))
            sql += ") "
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
            result = {row["key"]: row["value"] for row in result}

        if as_value_list:
            result = [row["value"] for row in result]

        return result

    def remove(self, key):
        deletions = self._delete("DELETE FROM registry WHERE key=?", (key,))
        cherrypy.engine.publish("app-log", "registry", "clear_key:{}".format(key), deletions)
        return deletions

    def firstKey(self, value=None):
        result = self.search(value=value, limit=1)

        if len(result) > 0:
            return result[0]["key"]
        else:
            return None

    def distinctKeys(self, key, value=None, stripPrefix=True):
        sql = "SELECT distinct key FROM registry WHERE (1) AND key LIKE ?"

        key = key.replace("*", "%")

        rows = self._select(sql, [key])

        keys = [row["key"] for row in rows]

        if stripPrefix:
            return [key.split(":", 1).pop() for key in keys]

        return keys
