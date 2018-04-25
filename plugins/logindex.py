import cherrypy
import os
import os.path
from collections import deque
import re
import pendulum
from . import mixins
from . import decorators


class Plugin(cherrypy.process.plugins.SimplePlugin, mixins.Sqlite):

    def __init__(self, bus):
        cherrypy.process.plugins.SimplePlugin.__init__(self, bus)
        self.db_path = self._path("logindex.sqlite")
        self.queue = deque()

        self._create("""
        PRAGMA journal_mode=WAL;

        CREATE TABLE IF NOT EXISTS logs (
            unix_timestamp integer,
            datestamp,
            hash,
            source_file,
            source_offset integer,
            ip collate nocase,
            host collate nocase,
            uri collate nocase,
            query collate nocase,
            statusCode integer,
            method collate nocase,
            agent collate nocase,
            agent_domain collate nocase,
            classification collate nocase,
            country collate nocase,
            region collate nocase,
            city collate nocase,
            latitude real,
            longitude real,
            cookie collate nocase,
            referrer collate nocase,
            referrer_domain collate nocase,
            logline,
            UNIQUE(hash)
        );

        CREATE INDEX IF NOT EXISTS index_datestamp
            ON logs (datestamp desc);
        CREATE INDEX IF NOT EXISTS index_ip
            ON logs(ip);
        CREATE INDEX IF NOT EXISTS index_host
            ON logs(host);
        CREATE INDEX IF NOT EXISTS index_uri
            ON logs(uri);
        CREATE INDEX IF NOT EXISTS index_statusCode
            ON logs(statusCode);
        CREATE INDEX IF NOT EXISTS index_method
            ON logs(method);
        CREATE INDEX IF NOT EXISTS index_agent_domain
            ON logs(agent_domain);
        CREATE INDEX IF NOT EXISTS index_classification
            ON logs(classification);
        CREATE INDEX IF NOT EXISTS index_country
            ON logs(country);
        CREATE INDEX IF NOT EXISTS index_city
            ON logs(city);
        CREATE INDEX IF NOT EXISTS index_cookie
            ON logs(cookie);

        CREATE TABLE IF NOT EXISTS reverse_ip (
            ip,
            reverse_host,
            reverse_domain,
            organization,
            updated DEFAULT NULL,
            UNIQUE(ip)
        );

        CREATE TRIGGER IF NOT EXISTS reverse_ip_after_update
        AFTER UPDATE ON reverse_ip
        BEGIN
        UPDATE reverse_ip SET updated=CURRENT_TIMESTAMP WHERE ip=new.ip;
        END;

        CREATE INDEX IF NOT EXISTS index_reverse_domain
            ON reverse_ip(reverse_domain);
        """)

    def start(self):
        self.bus.subscribe('logindex:parse', self.parse)
        self.bus.subscribe('logindex:reversal', self.reversal)
        self.bus.subscribe('logindex:enqueue', self.enqueue)
        self.bus.subscribe('logindex:process_queue', self.process_queue)
        self.bus.subscribe('logindex:query', self.query)
        self.bus.subscribe('logindex:query:reverse_ip', self.query_reverse_ip)
        self.bus.subscribe('logindex:precache', self.preCache)

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

    @decorators.log_runtime
    def enqueue(self, start_date, end_date):
        """Add log lines to the database for later parsing"""

        period = pendulum.period(start_date, end_date)

        if self.queue.count(period) > 0:
            cherrypy.engine.publish(
                "applog:add",
                "logindex",
                "enqueue",
                "Ignoring a request to queue an already-queued range"
            )

            return False

        self.queue.append(period)
        cherrypy.engine.publish("scheduler:add", 5, "logindex:process_queue")

        cherrypy.engine.publish(
            "applog:add",
            "logindex",
            "enqueue",
            "Queueing complete, processing scheduled"
        )

        return True

    def process_queue(self):
        try:
            period = self.queue[0]
            cherrypy.engine.publish(
                "applog:add",
                "logindex",
                "process_queue",
                "Queue is non-empty"
            )
        except IndexError:
            cherrypy.engine.publish("scheduler:add", 5, "logindex:parse")

            cherrypy.engine.publish(
                "applog:add",
                "logindex",
                "process_queue",
                "Queue is empty, parsing scheduled"
            )

            return

        for dt in period.range('days'):
            log_file = self.fileForDate(dt)
            if log_file:
                self.ingest_file(dt, log_file)

        self.queue.popleft()
        self.process_queue()

    def ingest_file(self, dt, file_path, batch_size=100):

        batch = []
        line_count = 0

        max_offset = self.lastKnownOffset(file_path)

        with open(file_path, "r") as f:

            # When indexing a previously indexed log file, max_offset
            # is the position of the last line that was added to the
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
                    self.filePathToSource(file_path),
                    offset,
                    cherrypy.engine.publish("hasher:md5", line).pop(),
                    line
                )

                batch.append(values)
                if len(batch) > batch_size:
                    line_count += self.insertLine(dt, batch)
                    batch = []

        if batch:
            line_count += self.insertLine(dt, batch)

        cherrypy.engine.publish(
            "applog:add",
            "logindex",
            "ingest_file",
            "Ingested {}".format(file_path)
        )

    @decorators.log_runtime
    def reversal(self, batch_size=50):
        records = self._select(
            """SELECT 0 as id, count(*) as value
            FROM reverse_ip
            WHERE updated IS NULL
            UNION
            SELECT rowid as id, ip as value
            FROM (
                SELECT rowid, ip
                FROM reverse_ip
                WHERE updated IS NULL
                LIMIT {}
            )""".format(batch_size)
        )

        batch = []

        unreversed_ips = records[0]["value"]

        cherrypy.engine.publish(
            "applog:add",
            "logindex",
            "reversal",
            "{} unreversed ips".format(unreversed_ips)
        )

        if unreversed_ips == 0:
            cherrypy.engine.publish("scheduler:add", 1, "logindex:precache")
            return

        for record in records[1:]:
            facts = cherrypy.engine.publish(
                "ip:reverse",
                record["value"]
            ).pop()

            batch.append((
                facts.get("reverse_host"),
                facts.get("reverse_domain"),
                record["id"],
            ))

        self._update(
            """UPDATE reverse_ip
            SET reverse_host=?, reverse_domain=?
            WHERE rowid=?""",
            batch
        )

        cherrypy.engine.publish("scheduler:add", 5, "logindex:reversal")

    @decorators.log_runtime
    def parse(self, batch_size=100):
        """Parse previously-added log lines"""

        select_sql = """
        SELECT 0 as id, count(*) as value
        FROM logs
        WHERE ip IS NULL
        UNION
        SELECT rowid as id, logline as value
        FROM logs
        WHERE ip IS NULL
        LIMIT {}""".format(batch_size)

        update_sql = """UPDATE logs SET unix_timestamp=?, datestamp=?, ip=?,
        host=?, uri=?, query=?, statusCode=?, method=?, agent=?,
        agent_domain=?, classification=?, country=?, region=?, city=?,
        latitude=?, longitude=?, cookie=?, referrer=?,
        referrer_domain=?  WHERE rowid=?"""

        records = self._select(select_sql)

        unparsed_rows = records[0]["value"]

        cherrypy.engine.publish(
            "applog:add",
            "logindex",
            "parse",
            "{} unparsed rows".format(unparsed_rows)
        )

        if unparsed_rows == 0:
            cherrypy.engine.publish("scheduler:add", 1, "logindex:reversal")
            return

        batch = []
        ips = set()

        ip_facts_cache = {}
        agent_cache = {}

        for record in records[1:]:
            fields = cherrypy.engine.publish(
                "parse:appengine",
                record["value"]
            ).pop()

            ip = fields["ip"]

            ips.add(ip)

            if ip in ip_facts_cache:
                ip_facts = ip_facts_cache[ip]
            else:
                ip_facts = cherrypy.engine.publish("ip:facts", ip).pop()
                ip_facts_cache[ip] = ip_facts

            geo = ip_facts.get("geo", {})

            fields["country"] = fields.get("country", geo.get("country_code"))
            fields["region"] = fields.get("region", geo.get("region_code"))
            fields["city"] = fields.get("city", geo.get("city"))
            fields["latitude"] = fields.get("latitude", geo.get("latitude"))
            fields["longitude"] = fields.get("latitude", geo.get("longitude"))

            agent = fields.get("agent", "")
            if agent in agent_cache:
                fields["agent_domain"] = agent_cache[agent]["agent_domain"]
            else:
                agent_url_matches = re.search(
                    "https?://(www\.)?(.*?)[/; ]",
                    agent
                )

                if agent_url_matches:
                    fields["agent_domain"] = agent_url_matches.group(2).lower()

                agent_cache[agent] = {
                    "agent_domain": fields.get("agent_domain"),
                }

            values = (
                fields.get("unix_timestamp"),
                fields.get("datestamp"),
                fields.get("ip"),
                fields.get("host"),
                fields.get("uri"),
                fields.get("query"),
                fields.get("statusCode"),
                fields.get("method"),
                fields.get("agent"),
                fields.get("agent_domain"),
                fields.get("classification"),
                fields.get("country"),
                fields.get("region"),
                fields.get("city"),
                fields.get("latitude"),
                fields.get("longitude"),
                fields.get("cookie"),
                fields.get("referrer"),
                fields.get("referrer_domain"),
                record["id"]
            )

            batch.append(values)
            if len(batch) > batch_size:
                self._update(update_sql, batch)
                batch = []

        if batch:
            self._update(update_sql, batch)

        self._insert(
            """INSERT OR IGNORE INTO reverse_ip (ip) VALUES (?)""",
            {(ip,) for ip in ips}
        )

        cherrypy.engine.publish("scheduler:add", 1, "logindex:parse")

    @decorators.log_runtime
    def insertLine(self, dt, records):
        if not records:
            return 0

        sql = """INSERT OR IGNORE INTO logs
        (source_file, source_offset, hash, logline)
        VALUES (?, ?, ?, ?)"""

        self._insert(sql, records)

        return len(records)

    @decorators.log_runtime
    def query(self, q, for_precache=False):
        parsed_query = cherrypy.engine.publish("parse:log_query", q).pop()

        sql = """SELECT unix_timestamp, logs.ip,
        host, uri, query as "query [querystring]",
        statusCode, method, agent_domain, classification, country,
        region, city, latitude, longitude, cookie,
        referrer, referrer_domain, logline
        FROM logs
        WHERE {}""".format(parsed_query)

        if for_precache:
            return self._selectToCache(sql, ())
        else:
            query_plan = self._explain(sql, ())
            result = self._select(sql, (), cacheable=True)
            return (result, query_plan)

    @decorators.log_runtime
    def query_reverse_ip(self, ips=()):

        placeholders = "?, " * len(ips)

        sql = """SELECT ip, reverse_domain
        FROM reverse_ip
        WHERE ip IN ({})""".format(placeholders[:-2])

        result = self._select(sql, tuple(ips))

        return {row["ip"]: row["reverse_domain"] for row in result}

    @decorators.log_runtime
    def preCache(self):
        saved_queries = cherrypy.engine.publish(
            "registry:search",
            "visitors*",
            key_slice=1
        ).pop()

        self._dropCacheTables()

        for query in saved_queries:
            self.query(query["value"], for_precache=True)
