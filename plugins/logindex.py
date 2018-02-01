import cherrypy
import os
import fnmatch
import os.path
import zlib
import re
from . import mixins
from . import decorators

class Plugin(cherrypy.process.plugins.SimplePlugin, mixins.Sqlite):

    def __init__(self, bus):
        cherrypy.process.plugins.SimplePlugin.__init__(self, bus)
        self.db_path = self._path("logindex.sqlite")


        self._create("""
        CREATE TABLE IF NOT EXISTS logs (
            year integer,
            month integer,
            day integer,
            hour integer,
            timestamp,
            timestamp_unix integer,
            checksum,
            source_file,
            source_offset integer,
            ip,
            ip_reverse_host,
            ip_reverse_domain,
            organization,
            host,
            uri,
            query,
            statusCode integer,
            method,
            agent,
            agent_domain,
            classification,
            country,
            region,
            city,
            postal_code,
            latitude real,
            longitude real,
            cookie,
            referrer,
            referrer_domain,
            logline,
            UNIQUE(checksum)
        );
        CREATE INDEX IF NOT EXISTS index_year ON logs(year);
        CREATE INDEX IF NOT EXISTS index_month ON logs(month);
        CREATE INDEX IF NOT EXISTS index_day ON logs(day);
        CREATE INDEX IF NOT EXISTS index_ip ON logs(ip);
        CREATE INDEX IF NOT EXISTS index_ip_reverse_domain ON logs(ip_reverse_domain);
        CREATE INDEX IF NOT EXISTS index_host ON logs(host);
        CREATE INDEX IF NOT EXISTS index_uri ON logs(uri);
        CREATE INDEX IF NOT EXISTS index_statusCode ON logs(statusCode);
        CREATE INDEX IF NOT EXISTS index_method ON logs(method);
        CREATE INDEX IF NOT EXISTS index_agent_domain ON logs(agent_domain);
        CREATE INDEX IF NOT EXISTS index_classification ON logs(classification);
        CREATE INDEX IF NOT EXISTS index_country ON logs(country);
        CREATE INDEX IF NOT EXISTS index_city ON logs(city);
        CREATE INDEX IF NOT EXISTS index_cookie ON logs(cookie);
        """)

    def start(self):
        self.bus.subscribe('logindex:parse', self.parse)
        self.bus.subscribe('logindex:enqueue', self.enqueue)
        self.bus.subscribe('logindex:schedule_parse', self.scheduleParse)
        self.bus.subscribe('logindex:query', self.query)
        self.bus.subscribe('logindex:precache', self.preCache)
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

    def filePathToSource(self, path):
        basename = os.path.basename(path)
        return os.path.splitext(basename)[0]

    def scheduleParse(self):
        sql = """SELECT count(*) as total FROM logs WHERE ip IS NULL"""
        row = self._selectOne(sql)

        cherrypy.engine.publish("applog:add", self, "unparsed_rows", row["total"])

        cherrypy.log("logindex found {} unparsed rows".format(row["total"]))

        if row["total"] == 0:
            cherrypy.engine.publish(
                "scheduler:add",
                10,
                "logindex:precache"
            )
        else:
            cherrypy.engine.publish(
                "scheduler:add",
                10,
                "logindex:parse"
            )

    @decorators.log_runtime_in_applog
    def enqueue(self, dt, batch_size=100):
        """Add log lines to the database for later parsing"""
        batch = []
        line_count = 0

        log_file = self.fileForDate(dt)
        if not log_file:
            return False

        max_offset = self.lastKnownOffset(log_file)

        with open(log_file, "r") as f:

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

    @decorators.log_runtime_in_applog
    def parse(self, batch_size=100):
        """Parse previously-added log lines"""
        select_sql = "SELECT rowid, logline FROM logs WHERE ip IS NULL LIMIT {}".format(batch_size)

        update_sql = """
        UPDATE logs SET year=?, month=?, day=?, hour=?, timestamp=?,
        timestamp_unix=?, ip=?, ip_reverse_host=?, ip_reverse_domain=?, organization=?, host=?, uri=?, query=?, statusCode=?, method=?, agent=?, agent_domain=?, classification=?, country=?, region=?, city=?,
        latitude=?, longitude=?, postal_code=?, cookie=?, referrer=?, referrer_domain=?
        WHERE rowid=?"""

        records = self._select(select_sql, ())
        batch = []

        ip_facts_cache = {}
        agent_cache = {}

        for record in records:
            fields = cherrypy.engine.publish("parse:appengine", record["logline"]).pop()

            ip = fields["ip"]

            if ip in ip_facts_cache:
                ip_facts = ip_facts_cache[ip]
            else:
                ip_facts = cherrypy.engine.publish("ip:facts", ip).pop()
                ip_facts_cache[ip] = ip_facts

            geo = ip_facts.get("geo", {})

            fields["country"] = fields["country"] or geo.get("country_code")
            fields["region"] = fields["region"] or geo.get("region_code")
            fields["city"] = fields["city"] or geo.get("city")
            fields["latitude"] = fields["latitude"] or geo.get("latitude")
            fields["longitude"] = fields["latitude"] or geo.get("longitude")
            fields["postal_code"] = geo.get("postal_code")
            fields["ip_reverse_host"] = ip_facts.get("reverse_host")
            fields["ip_reverse_domain"] = ip_facts.get("reverse_domain")
            fields["organization"] = ip_facts.get("organization")

            agent = fields.get("agent", "")
            if agent in agent_cache:
                fields["agent_domain"] = agent_cache[agent]["agent_domain"]
            else:
                agent_url_matches = re.search("https?://(www\.)?(.*?)[/; ]", agent)

                if agent_url_matches:
                    fields["agent_domain"] = agent_url_matches.group(2).lower()

                agent_cache[agent] = {
                    "agent_domain": fields.get("agent_domain"),
                }

            values = (
                fields.get("year"),
                fields.get("month"),
                fields.get("day"),
                fields.get("hour"),
                fields.get("timestamp"),
                fields.get("timestamp_unix"),
                fields.get("ip"),
                fields.get("ip_reverse_host"),
                fields.get("ip_reverse_domain"),
                fields.get("organization"),
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
                fields.get("postal_code"),
                fields.get("cookie"),
                fields.get("referrer"),
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

    @decorators.log_runtime_in_applog
    def insertLine(self, dt, records):
        if not records:
            return 0

        sql = """INSERT OR IGNORE INTO logs
        (source_file, source_offset, checksum, logline)
        VALUES (?, ?, ?, ?)"""

        self._insert(sql, records)

        return len(records)

    @decorators.log_runtime_in_applog
    def query(self, q, for_precache=False):
        parsed_query = cherrypy.engine.publish("parse:log_query", q).pop()

        sql = """SELECT year, month, day, hour, timestamp as "timestamp [datetime]",
        timestamp_unix, ip, ip_reverse_host, ip_reverse_domain, organization, host, uri,
        query as "query [querystring]", statusCode, method, agent_domain, classification,
        country, region, city, postal_code, latitude, longitude, cookie, referrer,
        referrer_domain, logline
        FROM logs
        WHERE {}
        ORDER BY timestamp_unix DESC""".format(parsed_query)

        if for_precache:
            return self._selectToCache(sql, ())
        else:
            return self._select(sql, (), cacheable=True)

    @decorators.log_runtime_in_applog
    def preCache(self):
        saved_queries = cherrypy.engine.publish(
            "registry:search",
            "visitors*",
            key_slice=1
        ).pop()

        self._dropCacheTables()

        for query in saved_queries:
            self.query(query["value"], for_precache=True)
