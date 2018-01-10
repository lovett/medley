import cherrypy
import os
from cherrypy.process import plugins
from collections import defaultdict
import fnmatch
import os.path
import zlib
from . import mixins

class Plugin(plugins.SimplePlugin, mixins.Sqlite):

    def __init__(self, bus):
        """The tables of this database map byte indexes within log files to
        one or more keys, making it possible to select a subset of log
        lines across one or more log files by seeking to specific
        indexes.

        The table itself acts as an index, but there is also a
        database-level index on the key field.
        """

        plugins.SimplePlugin.__init__(self, bus)
        self.db_path = self._path("logindex.sqlite")

        self.table_fields = "year, month, day, hour, timestamp, timestamp_unix, checksum, source_file, source_offset, ip, host, uri, query, statusCode, method, agent, country, city, cookie, referrer_domain, logline"
        self._create("""
        CREATE TABLE IF NOT EXISTS logs (
            {},
            UNIQUE(checksum)
        );
        CREATE INDEX IF NOT EXISTS index_ip ON logs(ip);
        CREATE INDEX IF NOT EXISTS index_host ON logs(host);
        CREATE INDEX IF NOT EXISTS index_uri ON logs(uri);
        CREATE INDEX IF NOT EXISTS index_statusCode ON logs(statusCode);
        CREATE INDEX IF NOT EXISTS index_method ON logs(method);
        CREATE INDEX IF NOT EXISTS index_agent ON logs(agent);
        CREATE INDEX IF NOT EXISTS index_country ON logs(country);
        CREATE INDEX IF NOT EXISTS index_city ON logs(city);
        CREATE INDEX IF NOT EXISTS index_cookie ON logs(cookie);
        """.format(self.table_fields))

    def start(self):
        self.bus.subscribe('logindex:files', self.fileList)
        self.bus.subscribe('logindex:file_for_date', self.fileForDate)
        self.bus.subscribe('logindex:parse', self.parse)
        self.bus.subscribe('logindex:enqueue', self.enqueue)
        self.bus.subscribe('logindex:schedule_parse', self.scheduleParse)
        self.scheduleParse()

    def stop(self):
        pass

    def getRoot(self):
        """Look up the root path for indexable log files in the registry"""
        key = "logindex:root"
        memorize_hit, memorize_value = cherrypy.engine.publish(
            "memorize:get",
            key
        ).pop()

        if memorize_hit:
            return memorize_value

        value = cherrypy.engine.publish(
            "registry:first_value",
            "logindex:root"
        ).pop()

        if value:
            cherrypy.engine.publish("memorize:set", key, value)

        return value

    def lastKnownOffset(self, path):
        sql = """SELECT source_offset FROM logs WHERE source_file=?
                  ORDER BY source_offset DESC LIMIT 1"""

        source = self.filePathToSource(path)

        row = self._selectOne(
            sql,
            (source,)
        )

        if row:
            return row["source_offset"]

        return 0

    def fileList(self, full_paths=False, ext="log"):
        """Returns a list of files matching an extension"""

        root = self.getRoot()

        files = [
            os.path.join(dirpath, f)
            for dirpath, dirnames, files in os.walk(root)
            for f in fnmatch.filter(files, "*.{}".format(ext))
        ]

        if full_paths:
            return files
        else:
            return [os.path.basename(f) for f in files]

    def fileForDate(self, dt):
        """The filesystem path of the log file for the given date"""

        root = self.getRoot()

        log_file = "{}/{}/{}".format(
            root,
            dt.strftime("%Y-%m"),
            dt.strftime("%Y-%m-%d.log")
        )

        if not os.path.isfile(log_file):
            return False

        return log_file

    def filePathToSource(self, path):
        basename = os.path.basename(path)
        return os.path.splitext(basename)[0]

    def scheduleParse(self):
        sql = """SELECT count(*) as "total [int]" FROM logs WHERE ip IS NULL"""
        row = self._selectOne(sql)

        if row["total"] == 0:
            return

        cherrypy.engine.publish(
            "scheduler:add",
            5,
            "logindex:parse"
        )

    def enqueue(self, dt, batch_size=100):
        """Add log lines to the database for later parsing"""
        batch = []
        line_count = 0

        log_file = self.fileForDate(dt)
        if not log_file:
            return False

        max_offset = self.lastKnownOffset(log_file)

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

                values = (
                    self.filePathToSource(log_file),
                    offset,
                    cherrypy.engine.publish("checksum:string", line).pop(),
                    line
                )

                batch.append(values)
                if len(batch) > batch_size:
                    line_count += self.insertLine(dt, batch)
                    batch = []

        if batch:
            line_count += self.insertLine(dt, batch)

        return line_count

    def parse(self, batch_size=100):
        """Parse previously-added log lines"""
        select_sql = "SELECT rowid, logline FROM logs WHERE ip IS NULL LIMIT {}".format(batch_size)

        update_sql = """
        UPDATE logs SET year=?, month=?, day=?, hour=?, timestamp=?,
        timestamp_unix=?, ip=?, host=?, uri=?, query=?, statusCode=?, method=?,
        agent=?, country=?, city=?, cookie=?, referrer_domain=?
        WHERE rowid=?"""

        records = self._select(select_sql, ())
        batch = []

        for record in records:
            fields = cherrypy.engine.publish("parse:appengine", record["logline"]).pop()

            values = (
                fields.get("year"),
                fields.get("month"),
                fields.get("day"),
                fields.get("hour"),
                fields.get("timestamp"),
                fields.get("timestamp_unix"),
                fields.get("ip"),
                fields.get("host"),
                fields.get("uri"),
                fields.get("query"),
                fields.get("statusCode"),
                fields.get("method"),
                fields.get("agent"),
                fields.get("country"),
                fields.get("city"),
                fields.get("cookie"),
                fields.get("referrer_domain"),
                record["rowid"]
            )

            batch.append(values)
            if len(batch) > batch_size:
                self._update(update_sql, batch)
                batch = []

        if batch:
            self._update(update_sql, batch)

        self.scheduleParse()


    def insertLine(self, dt, records):
        sql = "INSERT OR IGNORE INTO logs (source_file, source_offset, checksum, logline) VALUES (?, ?, ?, ?)"
        if records:
            self._insert(sql, records)

        return len(records)
