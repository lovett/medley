import cherrypy
import sqlite3
import os.path
import util.sqlite_converters

class Sqlite:
    def _path(self, name):
        return os.path.join(
            cherrypy.config.get("database_dir"),
            name
        )

    def _registerConverters(self):
        sqlite3.register_converter("created", util.sqlite_converters.convert_date)
        sqlite3.register_converter("binary", util.sqlite_converters.convert_binary)
        print("registered converters")

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

    def _insert(self, query, values):
        con = self._open()
        with con:
            con.executemany(query, values)
            cur = con.cursor()
            rowid = cur.lastrowid
        con.close()
        return rowid


    def _delete(self, query, values):
        con = self._open()
        with con:
            rows = con.execute(query, values).rowcount
        con.close()
        return rows

    def _selectOne(self, query, values):
        con = self._open()
        con.row_factory = sqlite3.Row
        with con:
            cur = con.cursor()
            cur.execute(query, values)
            row = cur.fetchone()

        return row or {}