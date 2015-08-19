import os.path
import time
import re
import sqlite3
import util.sqlite_converters
import pygeoip
import pickle
import netaddr
import util.fs
import hashlib
import util.parse
import functools
from urllib.parse import urlparse
from collections import defaultdict

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

captures_create_sql = """
CREATE TABLE IF NOT EXISTS captures (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_line, request, response,
    created DEFAULT CURRENT_TIMESTAMP
)
"""


cache_create_sql = """
CREATE TABLE IF NOT EXISTS cache (
    key UNIQUE NOT NULL,
    value, expires,
    created DEFAULT CURRENT_TIMESTAMP
)
"""

def setup(database_dir):
    global _databases

    roster = {
        "bookmarks": bookmarks_create_sql,
        "annotations": annotations_create_sql,
        "captures": captures_create_sql,
        "cache": cache_create_sql
    }

    try:
        os.mkdir(database_dir)
    except OSError as e:
        if "Permission denied" in str(e):
            raise e
        else:
            pass

    for name, sql in roster.items():
        path = os.path.join(database_dir, name + ".sqlite")
        conn = sqlite3.connect(path)
        cur = conn.cursor()
        cur.executescript(sql)
        conn.commit()
        conn.close()
        _databases[name] = path

def geoSetup(database_dir, download_url):
        db_path = database_dir
        db_path += "/" + os.path.basename(download_url)
        if db_path.endswith(".gz"):
            db_path = db_path[0:-3]

        try:
            _databases["geo"] = pygeoip.GeoIP(db_path)
        except IOError:
            _databases["geo"] = None

@functools.lru_cache()
def ipFacts(ip, geo_lookup=True):
    address = netaddr.IPAddress(ip)
    netblocks = getAnnotationsByPrefix("netblock")
    facts = {}

    for netblock in netblocks:
        if address in netaddr.IPNetwork(netblock["value"]):
            facts["organization"] = netblock["key"].split(":")[1]
            break

    annotations = util.db.getAnnotations("ip:{}".format(ip))
    if annotations:
        facts["annotations"] = [annotation["value"] for annotation in annotations]

    if geo_lookup:
        facts["geo"] = _databases["geo"].record_by_addr(ip)
    else:
        facts["geo"] = {}

    return facts

def getBookmarkById(bookmark_id):
    sqlite3.register_converter("created", util.sqlite_converters.convert_date)
    conn = sqlite3.connect(_databases["bookmarks"], detect_types=sqlite3.PARSE_COLNAMES)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    sql = """SELECT u.rowid, u.url, u.domain, m.title, u.created as 'created [created]', m.tags, m.comments
             FROM urls u, meta m
             WHERE u.rowid=m.url_id and u.rowid=?"""
    cur.execute(sql, (bookmark_id,))
    return cur.fetchone()

def getBookmarkByUrl(url):
    if not url:
        return False

    sqlite3.register_converter("created", util.sqlite_converters.convert_date)
    conn = sqlite3.connect(_databases["bookmarks"], detect_types=sqlite3.PARSE_COLNAMES)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    sql = """SELECT u.rowid, u.url, u.domain, m.title, u.created as 'created [created]', m.tags, m.comments
             FROM urls u, meta m
             WHERE u.url=? AND u.rowid=m.url_id"""
    cur.execute(sql, (url.lower(),))
    return cur.fetchone()

def deleteBookmark(id):
    conn = sqlite3.connect(_databases["bookmarks"], detect_types=sqlite3.PARSE_COLNAMES)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("DELETE FROM urls WHERE rowid=?", (int(id),))
    cur.execute("DELETE FROM meta WHERE url_id=?", (int(id),))
    conn.commit();
    return cur.rowcount

def getRecentBookmarks(limit=100):
    sqlite3.register_converter("created", util.sqlite_converters.convert_date)
    conn = sqlite3.connect(_databases["bookmarks"], detect_types=sqlite3.PARSE_COLNAMES)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    sql = """SELECT u.rowid, u.url, u.domain, m.title, u.created as 'created [created]', m.tags, m.comments, 'bookmark' as record_type
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
    cur.execute("INSERT OR REPLACE INTO urls (url, domain) VALUES (?, ?)", (url, parsed_url.netloc))
    conn.commit()
    url_id = cur.lastrowid
    cur.execute("""INSERT OR REPLACE INTO meta (url_id, title, comments, tags)
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

def saveAnnotation(key, value, replace=False):
    #unacceptable_chars = "[^\d\w -:;,\n]+"

    #key = re.sub(unacceptable_chars, "", key, flags=re.UNICODE).lower().strip()
    #value = re.sub(unacceptable_chars, "", value, flags=re.UNICODE).strip()

    conn = sqlite3.connect(_databases["annotations"])
    cur = conn.cursor()

    if replace:
        deleteAnnotationByKey(key)
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
        keys = [keys]

    sql = "SELECT id, key, value, created as 'created [created]' FROM annotations"

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

def getAnnotationById(id):
    sqlite3.register_converter("created", util.sqlite_converters.convert_date)
    conn = sqlite3.connect(_databases["annotations"], detect_types=sqlite3.PARSE_COLNAMES)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    sql = """SELECT id, key, value, datetime(created, 'localtime') as 'created [created]'
    FROM annotations WHERE id = ?"""

    cur.execute(sql, (id,))

    return cur.fetchone()

def getAnnotationsByKey(key):
    sqlite3.register_converter("created", util.sqlite_converters.convert_date)
    conn = sqlite3.connect(_databases["annotations"], detect_types=sqlite3.PARSE_COLNAMES)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    sql = """SELECT id, key, value, datetime(created, 'localtime') as 'created [created]'
    FROM annotations WHERE key LIKE ? ORDER BY key"""

    cur.execute(sql, (key,))

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

def deleteAnnotationByKey(key):
    conn = sqlite3.connect(_databases["annotations"])
    cur = conn.cursor()
    deleted_rows = cur.execute("DELETE FROM annotations WHERE key=?", (key,)).rowcount
    conn.commit()
    conn.close()
    return deleted_rows


def saveCapture(request, response):

    request_dict = {
        "headers": request.headers,
        "params": request.body.params
    }

    try:
        request_dict["json"] = request.json
    except:
        request_dict["json"] = None

    request_pickle = pickle.dumps(request_dict)

    response_dict = {
        "status": response.status
    }

    response_pickle = pickle.dumps(response_dict)

    conn = sqlite3.connect(_databases["captures"])
    cur = conn.cursor()

    sql = "INSERT INTO captures (request_line, request, response) VALUES (?, ?, ?)"
    cur.execute(sql, (request.request_line,
                      sqlite3.Binary(request_pickle),
                      sqlite3.Binary(response_pickle)))

    insert_id = cur.lastrowid
    conn.commit()
    conn.close()
    return insert_id

def getCaptures(request_line=None, limit=10):
    sqlite3.register_converter("created", util.sqlite_converters.convert_date)
    sqlite3.register_converter("pickle", util.sqlite_converters.convert_pickled)
    conn = sqlite3.connect(_databases["captures"], detect_types=sqlite3.PARSE_COLNAMES)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    sql = """SELECT id, request_line, request as 'request [pickle]',
             response as 'response [pickle]', created as 'created [created]'
             FROM captures
             WHERE request_line LIKE ?
             ORDER BY created DESC
             LIMIT ?"""

    if request_line:
        request_line_filter = "%{}%".format(request_line)
    else:
        request_line_filter = "%"

    cur.execute(sql, (request_line_filter, limit))

    return cur.fetchall()

def getPathHash(path, prefix):
    key = "hash:{}:{}".format(prefix, path)
    value = util.fs.file_hash(path)

    annotation = getAnnotationsByKey(key)

    if not annotation:
        return None
    else:
        return annotation[0]["value"]

def openLogIndex(db_dir, index_name=None):
    """Connect to or create an sqlite3 database under db_dir called logindexes.sqlite
    and create a table named after index_name.

    Each table of this database acts as an index to the lines of one
    or more log files.

    Each table also has a database-level index on the key field.

    Returns the opened connection.
    """

    db_path = os.path.join(
        db_dir,
        "logindex.sqlite"
    )

    db_conn = sqlite3.connect(db_path)
    db_conn.execute("PRAGMA synchronous=OFF")
    db_conn.execute("PRAGMA jounral_mode=MEMORY")

    if index_name:
        create_template = """
        CREATE TABLE IF NOT EXISTS {0} (
        date, key, offset, UNIQUE(date, key, offset));
        CREATE INDEX IF NOT EXISTS {0}_key_index ON {0}(key)
        """
        sql = create_template.format(index_name)
        db_conn.executescript(sql)
        db_conn.commit()

    return db_conn

def closeLogIndex(db_conn):
    db_conn.commit()
    db_conn.close()

def indexLogLines(db_conn, index_name, values):
    template = "INSERT OR IGNORE INTO {} (date, key, offset) VALUES (?, ?, ?)"
    sql = template.format(index_name)
    db_conn.executemany(sql, values)

def getLogOffsets(db_conn, index_name, keys=[]):
    db_conn.row_factory = sqlite3.Row
    cur = db_conn.cursor()
    template = "SELECT date, offset FROM {} WHERE key IN ({})"
    placeholders = ["?"] * len(keys)
    sql = template.format(index_name, ",".join(placeholders))

    cur.execute(sql, keys)

    offsets = defaultdict(list)

    for row in cur.fetchall():
        date = row["date"]
        offsets[date].append(row["offset"])

    return offsets

def getMaxOffset(db_conn, index_name, date):

    db_conn.row_factory = sqlite3.Row

    cur = db_conn.cursor()
    template = """SELECT offset
                  FROM {}
                  WHERE date=?
                  ORDER BY offset DESC
                  LIMIT 1"""
    sql = template.format(index_name)


    date_formatted = date.strftime("%Y-%m-%d")

    cur.execute(sql, (date_formatted,))

    row = cur.fetchone()

    if row:
        return row["offset"]
    else:
        return 0

def cacheGet(key):
    """Retrieve a value from the cache by its key"""

    db = sqlite3.connect(_databases["cache"], detect_types=sqlite3.PARSE_COLNAMES)
    db.row_factory = sqlite3.Row

    cachePurge(key, db)

    cur = db.cursor()
    db.execute("SELECT value FROM cache WHERE key=?", (key,))
    row = cur.fetchone()

    if row:
        return row["value"]
    else:
        return None

def cacheSet(key, value, lifespan_seconds=3600):
    """Add a value to the cache database"""

    db = sqlite3.connect(_databases["cache"])
    cur = db.cursor()

    expires = time.time() + int(lifespan_seconds)

    cur.execute("INSERT OR REPLACE INTO cache (key, value, expires) VALUES (?, ?, ?)", (key, value, expires))
    db.commit()
    db.close()

    return True

def cacheDel(key, conn=None):
    """Delete cache entries by key"""

    if not conn:
        db = sqlite3.connect(_databases["cache"])

    cur = db.cursor()
    cur.execute("DELETE FROM cache WHERE key=?", (key,))
    db.commit()

    if not conn:
        db.close()

    return True

def cachePurge(key, conn=None):
    """Delete expired cache entries by key"""

    if not conn:
        db = sqlite3.connect(_databases["cache"])
    else:
        db = conn

    expires = time.time()

    cur = db.cursor()
    cur.execute("DELETE FROM cache WHERE key=? AND expires < ?", (key, expires))
    db.commit()

    if not conn:
        db.close()

    return True
