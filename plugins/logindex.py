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
            unix_timestamp integer,
            checksum,
            source_file,
            source_offset integer,
            ip,
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

        CREATE INDEX IF NOT EXISTS index_ip ON logs(ip);
        CREATE INDEX IF NOT EXISTS index_host ON logs(host);
        CREATE INDEX IF NOT EXISTS index_uri ON logs(uri);
        CREATE INDEX IF NOT EXISTS index_statusCode ON logs(statusCode);
        CREATE INDEX IF NOT EXISTS index_method ON logs(method);
        CREATE INDEX IF NOT EXISTS index_agent_domain ON logs(agent_domain);
        CREATE INDEX IF NOT EXISTS index_classification ON logs(classification);
        CREATE INDEX IF NOT EXISTS index_country ON logs(country);
        CREATE INDEX IF NOT EXISTS index_city ON logs(city);
        CREATE INDEX IF NOT EXISTS index_cookie ON logs(cookie);

        CREATE TABLE IF NOT EXISTS reverse_ip (
            ip,
            reverse_host,
            reverse_domain,
            organization,
            updated DEFAULT NULL,
            UNIQUE(ip)
        );

        CREATE TRIGGER reverse_ip_after_update AFTER UPDATE ON reverse_ip
        BEGIN
        UPDATE reverse_ip SET updated=CURRENT_TIMESTAMP WHERE ip=new.ip;
        END;

        CREATE INDEX IF NOT EXISTS index_reverse_domain ON reverse_ip(reverse_domain);

        """)

    def start(self):
        self.bus.subscribe('logindex:parse', self.parse)
        self.bus.subscribe('logindex:reversal', self.reversal)
        self.bus.subscribe('logindex:enqueue', self.enqueue)
        self.bus.subscribe('logindex:query', self.query)
        self.bus.subscribe('logindex:precache', self.preCache)
        self.parse()

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
    def reversal(self, batch_size=10):
        records = self._select(
            "SELECT rowid, ip FROM reverse_ip WHERE updated IS NULL LIMIT {}".format(batch_size),
            ()
        )

        cherrypy.log("LOGNDX Found {} unreversed ips".format(len(records)))

        if len(records) == 0:
            cherrypy.engine.publish("scheduler:add", 1, "logindex:precache")
            return

        batch = []

        for record in records:
            facts = cherrypy.engine.publish("ip:reverse", record["ip"]).pop()

            batch.append((
                facts.get("reverse_host"),
                facts.get("reverse_domain"),
                record["rowid"],
            ))

        self._update(
            "UPDATE reverse_ip SET reverse_host=?, reverse_domain=? WHERE rowid=?",
            batch
        )

        cherrypy.engine.publish("scheduler:add", 5, "logindex:reversal")


    @decorators.log_runtime_in_applog
    def parse(self, batch_size=100):
        """Parse previously-added log lines"""
        select_sql = "SELECT rowid, logline FROM logs WHERE ip IS NULL LIMIT {}".format(batch_size)

        update_sql = """
        UPDATE logs SET unix_timestamp=?, ip=?, host=?, uri=?, query=?, statusCode=?, method=?, agent=?, agent_domain=?, classification=?, country=?, region=?, city=?,
        latitude=?, longitude=?, postal_code=?, cookie=?, referrer=?, referrer_domain=?
        WHERE rowid=?"""

        records = self._select(select_sql, ())

        cherrypy.log("LOGNDX Found {} unparsed rows".format(len(records)))

        if len(records) == 0:
            cherrypy.engine.publish("scheduler:add", 1, "logindex:reversal")
            return

        batch = []
        ips = set()

        ip_facts_cache = {}
        agent_cache = {}

        for record in records:
            fields = cherrypy.engine.publish("parse:appengine", record["logline"]).pop()

            ip = fields["ip"]

            ips.add(ip)

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
                fields.get("unix_timestamp"),
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

        self._insert(
            """INSERT OR IGNORE INTO reverse_ip (ip) VALUES (?)""",
            {(ip,) for ip in ips}
        )

        cherrypy.engine.publish("scheduler:add", 1, "logindex:parse")

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

        sql = """SELECT unix_timestamp, logs.ip,
        host, uri, query as "query [querystring]",
        statusCode, method, agent_domain, classification, country,
        region, city, postal_code, latitude, longitude, cookie,
        referrer, referrer_domain, logline, reverse_ip.reverse_domain
        FROM logs
        LEFT JOIN reverse_ip ON logs.ip=reverse_ip.ip
        WHERE {}
        ORDER BY unix_timestamp DESC""".format(parsed_query)


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

        cherrypy.log("LOGNDX Pre-cached {} queries".format(len(saved_queries)))
