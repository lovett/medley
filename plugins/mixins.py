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

    def _delete(self, query, values):
        con = self._open()
        with con:
            rows = con.execute(query, values).rowcount
        con.close()
        return rows

    def _select(self, query, values):
        con = self._open()
        con.row_factory = sqlite3.Row
        with con:
            cur = con.cursor()
            cur.execute(query, values)
            return cur.fetchall() or []

    def _selectOne(self, query, values=()):
        result = self._select(query, values)

        try:
            return result.pop()
        except IndexError:
            return {}
