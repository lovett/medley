import os.path
import time
import sqlite3
import cherrypy
import pickle
import util.sqlite_converters

class Cache:
    conn = None
    cur = None

    def __init__(self):
        db_dir = cherrypy.config.get("database_dir")
        path = os.path.join(db_dir, "cache.sqlite")
        sql = None
        if not os.path.isfile(path):
            sql = """CREATE TABLE IF NOT EXISTS cache (
            key UNIQUE NOT NULL,
            value, expires,
            created DEFAULT CURRENT_TIMESTAMP
            )"""

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

    def get(self, key):
        """Retrieve a value from the cache by its key"""
        self.purge(key)

        self.cur.execute("SELECT value, created FROM cache WHERE key=?", (key,))
        row = self.cur.fetchone()

        if row:
            return (pickle.loads(row["value"]), row["created"])
        else:
            return None

    def set(self, key, value, lifespan_seconds=3600):
        """Add a value to the cache database"""

        expires = time.time() + int(lifespan_seconds)

        self.cur.execute("INSERT OR REPLACE INTO cache (key, value, expires) VALUES (?, ?, ?)", (key, pickle.dumps(value), expires))
        self.conn.commit()

        return True

    def delete(self, key):
        """Delete cache entries by key"""
        self.cur.execute("DELETE FROM cache WHERE key=?", (key,))
        self.conn.commit()
        return True

    def purge(self, key):
        """Delete expired cache entries by key"""
        self.cur.execute("DELETE FROM cache WHERE key=? AND expires < ?", (key, time.time()))
        self.conn.commit()
        return True
