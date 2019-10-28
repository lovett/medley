"""Parse webserver log files for storage in an SQLite database."""

import os
import os.path
import re
import sqlite3
import typing
from collections import deque
from collections import defaultdict
import cherrypy
import pendulum
from . import mixins
from . import decorators


class Plugin(cherrypy.process.plugins.SimplePlugin, mixins.Sqlite):
    """A CherryPy plugin for searching webserver logs."""

    def __init__(self, bus: cherrypy.process.wspbus.Bus) -> None:
        cherrypy.process.plugins.SimplePlugin.__init__(self, bus)
        self.db_path = self._path("logindex.sqlite")
        self.queue: typing.Deque[pendulum.Period] = deque()

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
        CREATE INDEX IF NOT EXISTS index_ip_datestamp
            ON logs (ip, datestamp);
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
        CREATE INDEX IF NOT EXISTS index_region
            ON logs(region);
        CREATE INDEX IF NOT EXISTS index_cookie
            ON logs(cookie);
        CREATE INDEX IF NOT EXISTS index_source_file
            ON logs(source_file);

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

        CREATE TRIGGER IF NOT EXISTS backfill_region_after_insert
        AFTER INSERT ON logs
        FOR EACH ROW WHEN IFNULL(new.region, '') = ''
        BEGIN
        UPDATE logs SET region=(
            SELECT region FROM logs WHERE ip=new.ip AND region <> '' LIMIT 1
        ) WHERE rowid=new.rowid;
        END;

        CREATE TRIGGER IF NOT EXISTS backfill_city_after_insert
        AFTER INSERT ON logs
        FOR EACH ROW WHEN IFNULL(new.city, '') = ''
        BEGIN
        UPDATE logs SET city=(
            SELECT city FROM logs WHERE ip=new.ip AND city <> '' LIMIT 1
        ) WHERE rowid=new.rowid;
        END;

        CREATE INDEX IF NOT EXISTS index_reverse_domain
            ON reverse_ip(reverse_domain);

        """)

    def start(self) -> None:
        """Define the CherryPy messages to listen for.

        This plugin owns the logindex prefix.
        """

        self.bus.subscribe("server:ready", self.parse)
        self.bus.subscribe('logindex:parse', self.parse)
        self.bus.subscribe('logindex:reversal', self.reversal)
        self.bus.subscribe('logindex:alert', self.alert)
        self.bus.subscribe('logindex:enqueue', self.enqueue)
        self.bus.subscribe('logindex:process_queue', self.process_queue)
        self.bus.subscribe('logindex:query', self.query)
        self.bus.subscribe('logindex:query:reverse_ip', self.query_reverse_ip)
        self.bus.subscribe('logindex:count_visit_days', self.count_visit_days)

    @staticmethod
    def get_root() -> str:
        """Look up the root path for indexable log files in the registry"""

        key = "logindex:root"
        memorize_hit, memorize_value = typing.cast(
            typing.Tuple[bool, str],
            cherrypy.engine.publish(
                "memorize:get",
                key
            ).pop()
        )

        if memorize_hit:
            return memorize_value

        value: str = cherrypy.engine.publish(
            "registry:first_value",
            "logindex:root"
        ).pop()

        if value:
            cherrypy.engine.publish("memorize:set", key, value)

        return value

    @decorators.log_runtime
    def last_known_offset(self, path: str) -> int:
        """Figure out the last known position within a log file.

        Tracking the byte offset of each line within a file makes it
        possible to skip over previously-processed lines. Always
        starting from the beginning would take longer and longer as the
        size of the log file grew, and waste time."""

        source = self.file_path_to_source(path)

        row = self._selectOne(
            """SELECT COALESCE(MAX(source_offset), 0) as offset
            FROM logs
            WHERE source_file=?""",
            (source,)
        )

        if row:
            return typing.cast(int, row["offset"])

        return 0

    def file_for_date(self, log_date: pendulum) -> typing.Optional[str]:
        """The filesystem path of the log file for the given date"""

        root = self.get_root()

        subdir = log_date.strftime('%Y-%m')
        file = log_date.strftime('%Y-%m-%d.log')
        log_file = f"{root}/{subdir}/{file}"

        if not os.path.isfile(log_file):
            return None
        return log_file

    @staticmethod
    def file_path_to_source(path: str) -> str:
        """Extract the file name without extension of a file path."""

        basename = os.path.basename(path)
        return os.path.splitext(basename)[0]

    @decorators.log_runtime
    def enqueue(self, start_date: pendulum, end_date: pendulum) -> bool:
        """Schedule logfile processing.

        This is the start of the indexing process. The time period
        described by start_date and end_date determines how many days
        of logs will be processed.

        Other than scheduling work to occur in the future, not much
        happens here. The main goal is to prevent unnecessary work
        by allowing the same time period to be submitted multiple times.

        """

        period = pendulum.period(start_date, end_date)

        if self.queue.count(period) > 0:
            cherrypy.engine.publish(
                "applog:add",
                "logindex",
                "error",
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

    @decorators.log_runtime
    def process_queue(self) -> None:
        """Trigger log file ingestion and parsing.

        This is the first stage of processing, where queued time
        periods are matched with the relevant log files on the local
        filesystem and individual lines are ingested into the
        database.

        Once ingestion is complete, the next stage is parsing.

        """

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

        for day in period.range('days'):
            log_file = self.file_for_date(day)
            if log_file:
                self.ingest_file(log_file)

        self.queue.popleft()
        self.process_queue()

    @decorators.log_runtime
    def ingest_file(self, file_path: str, batch_size: int = 100) -> None:
        """Read new lines from a log file in batches."""

        batch = []
        line_count = 0

        max_offset = self.last_known_offset(file_path)

        with open(file_path, "r") as file_handle:

            # When indexing a previously indexed log file, max_offset
            # is the position of the last line that was added to the
            # database. Since it has already been seen, it can be
            # skipped. The next line is the first new line.
            if max_offset > 0:
                file_handle.seek(max_offset)
                file_handle.readline()

            while True:
                offset = file_handle.tell()
                line = file_handle.readline()

                if not line:
                    break

                values = (
                    self.file_path_to_source(file_path),
                    offset,
                    cherrypy.engine.publish("hasher:md5", line).pop(),
                    line
                )

                batch.append(values)
                if len(batch) > batch_size:
                    line_count += self.insert_line(batch)
                    batch = []

        if batch:
            line_count += self.insert_line(batch)

        cherrypy.engine.publish(
            "applog:add",
            "logindex",
            "ingest_file",
            file_path
        )

    @decorators.log_runtime
    def reversal(self, batch_size: int = 50) -> None:
        """Store the reverse hostname of an IP address."""

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
                LIMIT ?
            )""",
            (batch_size,)
        )

        batch = []

        unreversed_ips = records[0]["value"]

        cherrypy.engine.publish(
            "applog:add",
            "logindex",
            "unreversed_ips",
            unreversed_ips
        )

        if unreversed_ips == 0:
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
    def parse(self, batch_size: int = 100) -> None:
        """Parse log lines into fields

        The log line is initially inserted to the database as a single
        string. This is where the string gets broken into its
        constituent pieces.

        """

        update_sql = """UPDATE logs SET unix_timestamp=?, datestamp=?, ip=?,
        host=?, uri=?, query=?, statusCode=?, method=?, agent=?,
        agent_domain=?, classification=?, country=?, region=?, city=?,
        latitude=?, longitude=?, cookie=?, referrer=?,
        referrer_domain=?  WHERE rowid=?"""

        records = self._select(
            """SELECT 0 as id, count(*) as value
            FROM logs
            WHERE ip IS NULL
            UNION
            SELECT rowid as id, logline as value
            FROM logs
            WHERE ip IS NULL
            LIMIT ?""",
            (batch_size,)
        )

        if not records:
            return

        cherrypy.engine.publish(
            "applog:add",
            "logindex",
            "unparsed_rows",
            records[0]['value']
        )

        if records[0]["value"] == 0:
            cherrypy.engine.publish("scheduler:add", 1, "logindex:reversal")
            return

        batch = []
        ips = set()
        cache: typing.Dict[str, defaultdict] = {
            "ip": defaultdict(),
            "agent": defaultdict()
        }

        for record in records[1:]:
            fields = cherrypy.engine.publish(
                "parse:appengine",
                record["value"]
            ).pop()

            ip_address = fields["ip"]

            ips.add(ip_address)

            if ip_address not in cache["ip"]:
                cache["ip"][ip_address] = cherrypy.engine.publish(
                    "ip:facts", ip_address
                ).pop()

            geo = cache["ip"][ip_address]["geo"]

            fields["country"] = fields.get("country", geo["country_code"])
            fields["region"] = fields.get("region", geo["region_code"])
            fields["city"] = fields.get("city", geo["city"])
            fields["latitude"] = fields.get("latitude", geo["latitude"])
            fields["longitude"] = fields.get("latitude", geo["longitude"])

            agent = fields.get("agent", "")
            if agent in cache["agent"]:
                fields["agent_domain"] = cache["agent"][agent]["agent_domain"]
            else:
                agent_url_matches = re.search(
                    r"https?://(www\.)?(.*?)[/; ]",
                    agent
                )

                if agent_url_matches:
                    fields["agent_domain"] = agent_url_matches.group(2).lower()

                cache["agent"][agent] = {
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
            tuple({(ip,) for ip in ips})
        )

        cherrypy.engine.publish(
            "scheduler:add",
            1,
            "logindex:parse"
        )

        cherrypy.engine.publish(
            "scheduler:add",
            1,
            "logindex:alert",
            records[1]["id"],
            len(records)
        )

    def insert_line(
            self,
            records: typing.List[typing.Tuple[str, int, str, str]]
    ) -> int:
        """Write a batch of log lines to the database.

        This is the initial insert, where the line is added in its
        entirety. Parsing occurs at the next stage of processing."""

        if not records:
            return 0

        self._insert("""INSERT OR IGNORE INTO logs
        (source_file, source_offset, hash, logline)
        VALUES (?, ?, ?, ?)""", records)

        return len(records)

    @decorators.log_runtime
    def query(
            self,
            query: str
    ) -> typing.Tuple[typing.List[sqlite3.Row], typing.List[str]]:
        """Perform a search against parsed log lines."""

        parsed_query = cherrypy.engine.publish(
            "parse:log_query",
            query
        ).pop()

        sql = f"""SELECT unix_timestamp, logs.ip,
        host, uri, query as "query [querystring]",
        statusCode, method, agent_domain, classification, country,
        region, city, latitude, longitude, cookie,
        referrer, referrer_domain, logline
        FROM logs
        WHERE {parsed_query}
        ORDER BY unix_timestamp DESC"""  # nosec

        query_plan = self._explain(sql, ())
        result = self._select(sql, ())
        return (result, query_plan)

    @decorators.log_runtime
    def query_reverse_ip(
            self,
            ips: typing.Tuple[str, ...] = ()
    ) -> typing.Dict[str, str]:
        """Look up the reverse hostname of an IP address."""

        placeholders = ("?, " * len(ips))[:-2]

        sql = f"""SELECT ip, reverse_domain
        FROM reverse_ip
        WHERE ip IN ({placeholders})"""  # nosec

        result = self._select(sql, tuple(ips))

        return {row["ip"]: row["reverse_domain"] for row in result}

    @decorators.log_runtime
    def alert(self, earliest_id: int, count: int) -> None:
        """Send a notification for newly-parsed records that match
        previously-stored queries.

        """

        alert_queries = cherrypy.engine.publish(
            "registry:search",
            "logindex:alert:*",
            key_slice=2,
            as_dict=True
        ).pop()

        for name, query in alert_queries.items():
            parsed_query = cherrypy.engine.publish(
                "parse:log_query",
                query
            ).pop()

            sql = f"""SELECT distinct ip, uri
            FROM logs
            WHERE {parsed_query}
            AND rowid BETWEEN ? AND ?"""  # nosec

            records = self._select(
                sql,
                (earliest_id, earliest_id + count)
            )

            for record in records:
                url = cherrypy.engine.publish(
                    "url:internal",
                    "/visitors",
                    {"query": f"ip {record['ip']}\n{query}"},
                    trailing_slash=True
                ).pop()

                local_id = f"logindex-{name}-{record['ip']}"

                notification = {
                    "group": "web",
                    "title": "Logfile hit",
                    "body": f"{record['ip']} viewed {record['uri']}",
                    "url": url,
                    "localId": local_id,
                }

                cherrypy.engine.publish(
                    "notifier:send",
                    notification
                )

    @decorators.log_runtime
    def count_visit_days(
            self,
            ip_address: str
    ) -> typing.Dict[str, typing.Union[int, str]]:
        """Count the number of days an IP appears in the logs."""

        record = typing.cast(
            typing.Iterable[typing.Tuple[typing.Any, typing.Any]],
            self._selectOne(
                """SELECT count(DISTINCT substr(datestamp, 0, 11)) as count,
                min(datestamp) as 'earliest [date_with_hour]',
                max(datestamp) as 'latest [date_with_hour]'
                FROM logs
                WHERE ip=?""",
                (ip_address,)
            )
        )

        return dict(record)
