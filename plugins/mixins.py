import cherrypy
import sqlite3
import os.path

class Sqlite:
    def _path(self, name):
        return os.path.join(
            cherrypy.config.get("database_dir"),
            name
        )

    def _open(self):
        con = sqlite3.connect(self.db_path, detect_types=sqlite3.PARSE_COLNAMES)
        return con

    def _create(self, sql):
        if os.path.isfile(self.db_path):
            return

        con = self._open()
        con.cursor().executescript(sql)
        con.commit()
        con.close()


    def _multi(self, queries):
        con = self._open()
        with con:
            for query, params in queries:
                con.execute(query, params)
            con.commit()

    def _insert(self, query, values):
        con = self._open()
        with con:
            con.executemany(query, values)
            cur = con.cursor()
            rowid = cur.lastrowid
        con.close()

        # cannot return lastrowid because it is not populated during executemany
        return True

    def _update(self, query, values):
        con = self._open()
        with con:
            con.executemany(query, values)
        con.close()
        return True

    def _delete(self, query, values):
        con = self._open()
        with con:
            rows = con.execute(query, values).rowcount
        con.close()
        return rows

    def _select(self, query, values=()):
        con = self._open()
        con.row_factory = sqlite3.Row

        with con:
            cur = con.cursor()
            cur.execute(query, values)
            return cur.fetchall() or []

    def _explain(self, query, values=()):
        return self._select(
            "EXPLAIN QUERY PLAN {}".format(query),
            values
        )


    def _cacheTable(self, query):
        """The name of the table that will cache results for the specified query"""
        checksum = cherrypy.engine.publish("checksum:string", query).pop()
        return "cache_{}".format(checksum)


    def _tableNames(self):
        result = self._select(
            "SELECT name FROM sqlite_master WHERE type=?",
            ("table",)
        )
        return [row["name"] for row in result]


    def _dropCacheTables(self):
        """Remove all existing cache tables"""
        delete_queries = [
            ("DROP TABLE {}".format(table), ())
            for table in self._tableNames()
            if table.startswith("cache_")
        ]

        self._multi(delete_queries)

    def _selectToCache(self, query, values):
        """Send the results of a query to a cache table

        This is the sqlite way of doing "select into"
        """
        cache_table = self._cacheTable(query)

        con = self._open()
        with con:
            cur = con.cursor()

            # This delete is redundant with _dropCacheTables(), but it allows
            # a single cache to be cleaned up, instead of all of them.
            cur.execute("DROP TABLE IF EXISTS {}".format(cache_table))

            cur.execute(
                "CREATE TABLE {} AS {}".format(cache_table, query),
                values
            )

    def _selectOne(self, query, values=()):
        result = self._select(query, values)

        try:
            return result.pop()
        except IndexError:
            return {}

    def _selectFirst(self, query, values=()):
        result = self._select(query, values)

        try:
            row = result.pop()
            return row[0]
        except IndexError:
            return None
