import os.path
import sqlite3
import util.sqlite_converters
import markupsafe
from urllib.parse import urlparse

_databases = {}

bookmarks_create_sql = """
CREATE TABLE IF NOT EXISTS bookmarks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url VARCHAR(255) NOT NULL,
    domain VARCHAR(255),
    comments TEXT,
    created DATETIME DEFAULT CURRENT_TIMESTAMP
)
"""

annotations_create_sql = """
CREATE TABLE IF NOT EXISTS annotations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key VARCHAR(255) NOT NULL,
    value VARCHAR(255),
    created DATETIME DEFAULT CURRENT_TIMESTAMP
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
        cur.execute(sql)
        conn.commit()
        conn.close()
        _databases[name] = path

def saveBookmark(url, comments, created=None):

    parsed_url = urlparse(url)

    conn = sqlite3.connect(_databases["bookmarks"])
    cur = conn.cursor()
    cur.execute("INSERT INTO bookmarks (url, domain, comments, created) VALUES (?, ?, ?, ?)",
                (url, parsed_url.netloc, comments, created))
    conn.commit()
    bookmark_id = cur.lastrowid
    conn.close()
    return bookmark_id

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

def deleteAnnotation(annotation_id):
    annotation_id = int(annotation_id)
    conn = sqlite3.connect(_databases["annotations"])
    cur = conn.cursor()
    deleted_rows = cur.execute("DELETE FROM annotations WHERE id=?", (annotation_id,)).rowcount
    conn.commit()
    conn.close()
    return deleted_rows
