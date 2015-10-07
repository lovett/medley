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
import pickle
from urllib.parse import urlparse
from collections import defaultdict

_databases = {}

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


def cacheGet(key):
    """Retrieve a value from the cache by its key"""
    sqlite3.register_converter("created", util.sqlite_converters.convert_date)
    db = sqlite3.connect(_databases["cache"], detect_types=sqlite3.PARSE_COLNAMES)
    db.row_factory = sqlite3.Row

    cachePurge(key, db)

    cur = db.cursor()
    cur.execute("SELECT value, created FROM cache WHERE key=?", (key,))
    row = cur.fetchone()


    if row:
        return (pickle.loads(row["value"]), row["created"])
    else:
        return None

def cacheSet(key, value, lifespan_seconds=3600):
    """Add a value to the cache database"""

    db = sqlite3.connect(_databases["cache"])
    cur = db.cursor()

    expires = time.time() + int(lifespan_seconds)

    cur.execute("INSERT OR REPLACE INTO cache (key, value, expires) VALUES (?, ?, ?)", (key, pickle.dumps(value), expires))
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

    cur = db.cursor()
    cur.execute("DELETE FROM cache WHERE key=? AND expires < ?", (key, time.time()))
    db.commit()

    if not conn:
        db.close()

    return True
