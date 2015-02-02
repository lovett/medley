import os.path
import sqlite3
import util.sqlite_converters
import markupsafe
from urllib.parse import urlparse

_databases = {}

bookmarks_create_sql = """
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

annotations_create_sql = """
CREATE TABLE IF NOT EXISTS annotations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key VARCHAR(255) NOT NULL,
    value VARCHAR(255),
    created DEFAULT CURRENT_TIMESTAMP
)
"""

def setup(database_dir):
    global _databases

    roster = {
        "bookmarks": bookmarks_create_sql,
        "annotations": annotations_create_sql
    }

    for name, sql in roster.items():
        path = os.path.join(database_dir, name + ".sqlite")
        conn = sqlite3.connect(path)
        cur = conn.cursor()
        cur.executescript(sql)
        conn.commit()
        conn.close()
        _databases[name] = path


def getBookmarkById(bookmark_id):
    sqlite3.register_converter("created", util.sqlite_converters.convert_date)
    conn = sqlite3.connect(_databases["bookmarks"], detect_types=sqlite3.PARSE_COLNAMES)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    sql = """SELECT u.url, u.domain, m.title, u.created as 'created [created]', m.tags, m.comments
             FROM urls u, meta m
             WHERE u.rowid=m.url_id and u.rowid=?"""
    cur.execute(sql, (bookmark_id,))
    return cur.fetchone()

def getBookmarkByUrl(url):
    sqlite3.register_converter("created", util.sqlite_converters.convert_date)
    conn = sqlite3.connect(_databases["bookmarks"], detect_types=sqlite3.PARSE_COLNAMES)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    sql = """SELECT u.url, u.domain, m.title, u.created as 'created [created]', m.tags, m.comments
             FROM urls u, meta m
             WHERE u.url=? AND u.rowid=m.url_id"""
    cur.execute(sql, (url.lower(),))
    return cur.fetchone()

def getRecentBookmarks(limit=100):
    sqlite3.register_converter("created", util.sqlite_converters.convert_date)
    conn = sqlite3.connect(_databases["bookmarks"], detect_types=sqlite3.PARSE_COLNAMES)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    sql = """SELECT u.url, u.domain, m.title, u.created as 'created [created]', m.tags, m.comments, 'bookmark' as record_type
             FROM urls u, meta m
             WHERE u.rowid=m.url_id
             ORDER BY u.created DESC
             LIMIT ?"""
    cur.execute(sql, (limit,))
    return cur.fetchall()

def saveBookmark(url, title, comments=None, tags=None):
    parsed_url = urlparse(url)

    conn = sqlite3.connect(_databases["bookmarks"])
    cur = conn.cursor()
    cur.execute("INSERT INTO urls (url, domain) VALUES (?, ?)", (url, parsed_url.netloc))
    conn.commit()
    url_id = cur.lastrowid
    cur.execute("""INSERT INTO meta (url_id, title, comments, tags)
                VALUES (?, ?, ?, ?)""",
                (url_id, title, comments, tags))
    conn.commit()
    conn.close()
    return url_id

def saveBookmarkFulltext(url_id, fulltext):
    conn = sqlite3.connect(_databases["bookmarks"])
    cur = conn.cursor()
    cur.execute("UPDATE meta SET fulltext=? WHERE url_id=?",
                (fulltext, url_id))
    conn.commit()
    conn.close()
    return True


def saveAnnotation(key, value):

    key = markupsafe.escape(key)
    value = markupsafe.escape(value)

    conn = sqlite3.connect(_databases["annotations"])
    cur = conn.cursor()
    cur.execute("INSERT INTO annotations (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    annotation_id = cur.lastrowid
    conn.close()
    return annotation_id

def getAnnotations(keys=[], limit=0):
    sqlite3.register_converter("created", util.sqlite_converters.convert_date)

    conn = sqlite3.connect(_databases["annotations"], detect_types=sqlite3.PARSE_COLNAMES)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    if not isinstance(keys, list):
        keys = [markupsafe.escape(keys)]
    else:
        keys = [markupsafe.escape(key) for key in keys]

    sql = "SELECT id, key, value, datetime(created, 'localtime') as 'created [created]' FROM annotations"

    if keys:
        sql += " WHERE key IN ("
        sql += ", ".join("?" * len(keys))
        sql += ")"

    sql += " ORDER BY id DESC"

    if limit:
        sql += " LIMIT {}".format(limit)

    if keys:
        cur.execute(sql, keys)
    else:
        cur.execute(sql)

    return cur.fetchall()

def getAnnotationsByPrefix(prefix):
    sqlite3.register_converter("created", util.sqlite_converters.convert_date)
    conn = sqlite3.connect(_databases["annotations"], detect_types=sqlite3.PARSE_COLNAMES)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    prefix = "{}:%".format(prefix)

    sql = """SELECT id, key, value, datetime(created, 'localtime') as 'created [created]'
    FROM annotations WHERE key LIKE ? ORDER BY key"""

    cur.execute(sql, (prefix,))

    return cur.fetchall()


def deleteAnnotation(annotation_id):
    annotation_id = int(annotation_id)
    conn = sqlite3.connect(_databases["annotations"])
    cur = conn.cursor()
    deleted_rows = cur.execute("DELETE FROM annotations WHERE id=?", (annotation_id,)).rowcount
    conn.commit()
    conn.close()
    return deleted_rows
