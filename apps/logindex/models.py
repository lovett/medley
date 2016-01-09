import sys
import os.path
sys.path.append("../../")

import cherrypy
import sqlite3
import os.path
import fnmatch
import util.parse
from collections import defaultdict

class LogManager:

    conn = None
    cur = None
    log_dir = None

    def __init__(self, root):
        db_path = os.path.join(
            cherrypy.config.get("database_dir"),
            "logindex.sqlite"
        )
        self.conn = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_COLNAMES)
        self.conn.execute("PRAGMA synchronous=OFF")
        self.conn.execute("PRAGMA jounral_mode=MEMORY")
        self.conn.row_factory = sqlite3.Row
        self.cur = self.conn.cursor()
        self.log_dir = root

    def __del__(self):
        if self.conn:
            self.conn.close()

    def getList(self, full_paths=False):
        """Returns a list of all .log files in log_dir"""
        files = [os.path.join(dirpath, f)
                 for dirpath, dirnames, files in os.walk(self.log_dir)
                 for f in fnmatch.filter(files, "*.log")]

        if full_paths:
            return files
        else:
            return [os.path.basename(f) for f in files]


    def getPathForDate(self, date):
        """Returns the filesystem path of the log file for the given date"""
        log_file = "{}/{}/{}".format(
            self.log_dir,
            date.strftime("%Y-%m"),
            date.strftime("%Y-%m-%d.log"))

        if not os.path.isfile(log_file):
            return False
        else:
            return log_file

    def establishIndex(self, name):
        """Create an index table if one does not already exist

        The table maps byte indexes within log files to one or more
        keys, making it possible to select a subset of log lines across one
        or more log files by seeking to specific indexes.

        The table itself acts as an index, but there is also a
        database-level index on the key field.
        """

        sql = """
        CREATE TABLE IF NOT EXISTS {0} (
        date, key, offset, UNIQUE(date, key, offset));
        CREATE INDEX IF NOT EXISTS {0}_key_index ON {0}(key)
        """.format(name)
        self.conn.executescript(sql)
        self.conn.commit()

    def getMaxOffset(self, date, index_name):
        sql = """SELECT offset FROM {} WHERE date=?
                  ORDER BY offset DESC LIMIT 1""".format(index_name)

        date_formatted = date.strftime("%Y-%m-%d")

        self.cur.execute(sql, (date_formatted,))

        row = self.cur.fetchone()

        if row:
            return row["offset"]
        else:
            return 0

    def getLogOffsets(self, index_name, keys=[]):
        template = "SELECT date, offset FROM {} WHERE key IN ({})"
        placeholders = ["?"] * len(keys)
        sql = template.format(index_name, ",".join(placeholders))

        self.cur.execute(sql, keys)

        offsets = defaultdict(list)

        for row in self.cur.fetchall():
            date = row["date"]
            offsets[date].append(row["offset"])

        return offsets

    def index(self, date, by, match=None):
        batch = []
        line_count = 0

        log_file = self.getPathForDate(date)
        if not log_file:
            raise cherrypy.HTTPError(400, "No log for that date")

        index_name = by
        if match:
            lower_match = match.lower()
            index_name += "_" + lower_match
        self.establishIndex(index_name)

        insert_sql = "INSERT OR IGNORE INTO {} (date, key, offset) VALUES (?, ?, ?)".format(index_name)
        def insert(records=()):
            if not records:
                return 0

            self.conn.executemany(insert_sql, records)
            self.conn.commit()
            return len(records)


        if by == "ip":
            indexer = util.parse.appengine_ip
        else:
            indexer = util.parse.appengine

        max_offset = self.getMaxOffset(date, index_name)

        with open(log_file, "r") as f:

            # When indexing a previously index log, max_offset is the
            # position of the last line that was added to the
            # database. Since it has already been seen, it can be
            # skipped. The next line is the first new line.
            if max_offset > 0:
                f.seek(max_offset)
                f.readline()

            while True:
                offset = f.tell()
                line = f.readline()

                if not line:
                    break

                fields = indexer(line)

                # the field isn't present
                if not by in fields:
                    continue

                # the field doesn't match
                if match and (lower_match not in fields[by].lower()):
                    continue


                values = (
                    date.strftime("%Y-%m-%d"),
                    fields[by],
                    offset
                )

                batch.append(values)

                if len(batch) > 500:
                    line_count += insert(batch)
                    batch = []
        line_count += insert(batch)
        return line_count
