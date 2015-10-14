import os.path
import sqlite3
import cherrypy
import util.sqlite_converters

class Registry:

    conn = None
    cur = None

    def __init__(self):
        db_dir = cherrypy.config.get("database_dir")
        path = os.path.join(db_dir, "registry.sqlite")
        sql = None
        if not os.path.isfile(path):
            sql = """
CREATE TABLE IF NOT EXISTS registry (
    key VARCHAR(255) NOT NULL,
    value VARCHAR(255),
    created DEFAULT CURRENT_TIMESTAMP
)
"""
        sqlite3.register_converter("created", util.sqlite_converters.convert_date)
        self.conn = sqlite3.connect(path, detect_types=sqlite3.PARSE_COLNAMES)
        self.conn.row_factory = sqlite3.Row
        self.cur = self.conn.cursor()

        if sql:
            self.cur.executescript(sql)
            self.conn.commit()

    def __del__(self):
        if self.conn:
            self.conn.close()

    def add(self, key, value, replace=False):
        #unacceptable_chars = "[^\d\w -:;,\n]+"
        #key = re.sub(unacceptable_chars, "", key, flags=re.UNICODE).lower().strip()
        #value = re.sub(unacceptable_chars, "", value, flags=re.UNICODE).strip()

        if replace:
            self.removeByKey(key)

        self.cur.execute("INSERT INTO registry (key, value) VALUES (?, ?)", (key, value))
        self.conn.commit()
        return self.cur.lastrowid

    def remove(self, key=None, uid=None):
        if uid:
            deleted_rows = self.cur.execute("DELETE FROM registry WHERE rowid=?", (uid,)).rowcount
        else:
            deleted_rows = self.cur.execute("DELETE FROM registry WHERE key=?", (key,)).rowcount
        self.conn.commit()
        return deleted_rows

    def find(self, uid=None):
        sql = """SELECT rowid, key, value, created as 'created [created]'
        FROM registry
        WHERE rowid=?"""

        self.cur.execute(sql, (uid,))
        return self.cur.fetchall()

    def search(self, key=None, keys=[], limit=100):
        sql = "SELECT rowid, key, value, created as 'created [created]' FROM registry"
        params = None

        if len(keys) > 0:
            sql += " WHERE key IN ("
            sql += ", ".join("?" * len(keys))
            sql += ")"
        elif key:
            fuzzy = "*" in key
            key = key.replace("*", "%")

            if not fuzzy:
                sql += " WHERE key=?"
            else:
                sql += " WHERE KEY LIKE ?"

            params = (key,)
        sql += " ORDER BY rowid DESC"
        sql += " LIMIT {}".format(limit)

        if params:
            self.cur.execute(sql, params)
        else:
            self.cur.execute(sql)

        return self.cur.fetchall()

    def recent(self, limit=25):
        sql = """SELECT rowid, key, value, created as 'created [created]'
        FROM registry
        ORDER BY rowid DESC
        LIMIT ?"""
        self.cur.execute(sql, (limit,))
        return self.cur.fetchall()
