import os.path
import sqlite3
import cherrypy
import util.sqlite_converters
import requests
from urllib.parse import urlparse

class Archive:

    conn = None
    cur = None

    def __init__(self):
        db_dir = cherrypy.config.get("database_dir")
        path = os.path.join(db_dir, "archive.sqlite")
        sql = None
        if not os.path.isfile(path):
            sql = """
CREATE TABLE IF NOT EXISTS urls (
    url UNIQUE,
    created DEFAULT CURRENT_TIMESTAMP,
    domain
);

CREATE VIRTUAL TABLE IF NOT EXISTS meta USING fts4 (
    url_id, title, tags, comments,
    fulltext, tokenize=porter
);

CREATE INDEX IF NOT EXISTS url_domain ON urls (domain);
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

    def add(self, url, title, comments=None, tags=None):
        parsed_url = urlparse(url)

        self.cur.execute("INSERT OR REPLACE INTO urls (url, domain) VALUES (?, ?)", (url, parsed_url.netloc))
        self.conn.commit()

        url_id = self.cur.lastrowid

        self.cur.execute("""INSERT OR REPLACE INTO meta (url_id, title, comments, tags)
        VALUES (?, ?, ?, ?)""", (url_id, title, comments, tags))
        self.conn.commit()
        return url_id

    def addFullText(self, url_id, fulltext):
        self.cur.execute("UPDATE meta SET fulltext=? WHERE url_id=?", (fulltext, url_id))
        self.conn.commit()

    def remove(self, uid):
        self.cur.execute("DELETE FROM urls WHERE rowid=?", (int(uid),))
        self.cur.execute("DELETE FROM meta WHERE url_id=?", (int(uid),))
        self.conn.commit()
        return self.cur.rowcount

    def count(self, uid):
        sql = """SELECT count(*) as total FROM urls WHERE rowid=?"""
        self.cur.execute(sql, (int(uid),))
        self.conn.commit()
        row = self.cur.fetchone()
        return row["total"]

    def find(self, uid=None, url=None):
        sql = """SELECT u.rowid, u.url, u.domain, m.title,
            u.created as 'created [created]', m.tags, m.comments
            FROM urls u, meta m WHERE u.rowid=m.url_id"""

        if uid:
            sql += " AND u.rowid=?"
            self.cur.execute(sql, (uid,))
        elif url:
            sql += " AND u.url=?"
            self.cur.execute(sql, (url.lower(),))
        elif search:
            self.cur.execute(sql, (search,))

        return self.cur.fetchone()

    def search(self, search):
        sql = """SELECT u.rowid, u.url, u.domain, m.title,
            u.created as 'created [created]', m.tags, m.comments
            FROM urls u, meta m WHERE u.rowid=m.url_id AND meta MATCH ?
            ORDER BY u.created DESC"""
        self.cur.execute(sql, (search,))

        return self.cur.fetchall()

    def recent(self, limit=100):
        sql = """SELECT u.rowid, u.url, u.domain, m.title, case when m.fulltext is
        null then 0 else 1 end as has_fulltext, u.created as 'created [created]', m.tags, m.comments, 'bookmark' as record_type FROM urls u, meta m WHERE u.rowid=m.url_id ORDER BY u.created DESC LIMIT ?"""

        self.cur.execute(sql, (limit,))
        return self.cur.fetchall()

    def fetch(self, url):
        r = requests.get(
            url,
            timeout=5,
            allow_redirects=True,
            headers = {
                "User-Agent": "python"
            }
        )

        if r.status_code == requests.codes.ok:
            return r.text
        else:
            return None
