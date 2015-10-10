import os.path
import time
import re
import sqlite3
import util.sqlite_converters
import netaddr
import util.fs
import hashlib
import functools
import pickle
import apps.registry.models
import apps.geodb.models

_databases = {}

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

@functools.lru_cache()
def ipFacts(ip, geo_lookup=True):
    registry = apps.registry.models.Registry()
    address = netaddr.IPAddress(ip)
    netblocks = registry.find(key="netblock")
    facts = {}

    for netblock in netblocks:
        if address in netaddr.IPNetwork(netblock["value"]):
            facts["organization"] = netblock["key"].split(":")[1]
            break

    annotations = registry.find(key="ip:{}".format(ip))
    if annotations:
        facts["annotations"] = [annotation["value"] for annotation in annotations]

    if geo_lookup:
        geodb = apps.geodb.models.GeoDB()

        facts["geo"] = geodb.findByIp(ip)
    else:
        facts["geo"] = {}

    return facts

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
