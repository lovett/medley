import sqlite3
import util.sqlite_converters
from urllib.parse import urlparse

def saveBookmark(database, url, comments, created=None):

    parsed_url = urlparse(url)

    conn = sqlite3.connect(database)
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS bookmarks (id INTEGER PRIMARY KEY AUTOINCREMENT, url VARCHAR(255) NOT NULL, domain VARCHAR(255), comments TEXT, created DATETIME DEFAULT CURRENT_TIMESTAMP)")

    cur.execute("INSERT INTO bookmarks (url, domain, comments, created) VALUES (?, ?, ?, ?)",
                (url, parsed_url.netloc, comments, created))
    conn.commit()
    bookmark_id = cur.lastrowid
    conn.close()
    return bookmark_id
