"""Storage for food log entries."""

import re
import sqlite3
from typing import Any
from typing import Iterator
from typing import Optional
from typing import Tuple
from typing import Union
import cherrypy
from plugins import mixins
from plugins import decorators

SearchResult = Tuple[
    Iterator[sqlite3.Row], int
]

PlaceholderTuple = Tuple[Union[str, int], ...]


class Plugin(cherrypy.process.plugins.SimplePlugin, mixins.Sqlite):
    """Store foodlog entries via SQLite."""

    def __init__(self, bus: cherrypy.process.wspbus.Bus) -> None:
        cherrypy.process.plugins.SimplePlugin.__init__(self, bus)

        self.db_path = self._path("foodlog.sqlite")

    def setup(self) -> None:
        """Create the database."""

        self._create("""
        PRAGMA journal_mode=WAL;
        PRAGMA foreign_keys=ON;

        CREATE TABLE IF NOT EXISTS foodlog (
            id INTEGER PRIMARY KEY,
            consumed_on TEXT NOT NULL,
            foods_eaten TEXT NOT NULL,
            overate INT DEFAULT 0
        );

        CREATE VIRTUAL TABLE IF NOT EXISTS foodlog_fts USING fts5 (
            foods_eaten,
            content=foodlog,
            tokenize=porter
        );

        CREATE TRIGGER IF NOT EXISTS foodlog_after_insert
        AFTER INSERT ON foodlog
        BEGIN
        INSERT INTO foodlog_fts (rowid, foods_eaten)
        VALUES (new.rowid, new.foods_eaten);
        END;

        CREATE TRIGGER IF NOT EXISTS foodlog_after_update
        AFTER UPDATE OF foods_eaten ON foodlog
        BEGIN
        INSERT INTO foodlog_fts (foodlog_fts, rowid, foods_eaten)
            VALUES ('delete', old.rowid, old.foods_eaten);
        INSERT INTO foodlog_fts (rowid, foods_eaten)
            VALUES (new.rowid, new.foods_eaten);
        END;

        CREATE TRIGGER IF NOT EXISTS foodlog_after_delete
        AFTER DELETE ON foodlog
        BEGIN
        INSERT INTO foodlog_fts(foodlog_fts, rowid, foods_eaten)
            VALUES ('delete', old.rowid, old.foods_eaten);
        END;

        """)

    def start(self) -> None:
        """Define the CherryPy messages to listen for.

        This plugin owns the foodlog prefix.
        """

        self.bus.subscribe("server:ready", self.setup)
        self.bus.subscribe("foodlog:find", self.find)
        self.bus.subscribe("foodlog:activity", self.activity)
        self.bus.subscribe("foodlog:remove", self.remove)
        self.bus.subscribe("foodlog:search", self.search)
        self.bus.subscribe("foodlog:upsert", self.upsert)

    def find(self, entry_id: int) -> Optional[sqlite3.Row]:
        """Locate an entry by its ID."""

        return self._selectOne(
            """SELECT id, foods_eaten, overate,
            consumed_on as 'consumed_on [local_datetime]'
            FROM foodlog
            WHERE id=?""",
            (entry_id,)
        )

    @decorators.log_runtime
    def remove(self, entry_id: int) -> bool:
        """Delete an entry."""

        return self._execute(
            "DELETE FROM foodlog WHERE id=?",
            (entry_id,)
        )

    def activity(self, **kwargs: Any) -> Iterator[sqlite3.Row]:
        """Visualize a keyword search as an GitHub-style activity chart."""

        query = kwargs.get("query", "")

        sql = """WITH RECURSIVE calendar(days_ago, dt) AS
        (SELECT 0, datetime('now')
         UNION ALL SELECT days_ago+1, datetime(dt, '-1 day')
         FROM calendar LIMIT 364)
        SELECT days_ago, dt as 'date [local_datetime]', (
            SELECT count(*) FROM foodlog, foodlog_fts
            WHERE foodlog.id=foodlog_fts.rowid
            AND date(foodlog.consumed_on)=date(dt)
            AND foodlog_fts MATCH ?
        ) as tally
        FROM calendar
        ORDER BY days_ago DESC
        """

        placeholders: PlaceholderTuple = (query,)

        return self._select_generator(sql, placeholders)

    def search(self, **kwargs: Any) -> SearchResult:
        """Locate entries that match a keyword search."""

        limit = int(kwargs.get("limit", 20))
        offset = int(kwargs.get("offset", 20))
        query = kwargs.get("query", "")

        date_range = None
        date_match = re.search(r"\d{4}-\d{2}-\d{2}", query)
        if date_match:
            start_date = date_match.group(0)
            end_date = start_date
            query = query.replace(start_date, "")
            date_range = (start_date, end_date)

        if not date_range:
            date_match = re.search(r"\d{4}-\d{2}", query)
            if date_match:
                start = cherrypy.engine.publish(
                    "clock:from_format",
                    date_match.group(0),
                    "%Y-%m"
                ).pop()

                end = cherrypy.engine.publish(
                    "clock:shift",
                    start,
                    "month_end"
                ).pop()

                date_range = (
                    cherrypy.engine.publish(
                        "clock:format",
                        start,
                        "%Y-%m-%d"
                    ).pop(),
                    cherrypy.engine.publish(
                        "clock:format",
                        end,
                        "%Y-%m-%d"
                    ).pop()
                )
                query = query.replace(date_match.group(0), "")

        if not date_range:
            date_match = re.search(r"\d{4}", query)
            if date_match:
                year = date_match.group(0)
                date_range = (
                    year + "-01-01",
                    year + "-12-31"
                )

                query = query.replace(year, "")

        date_range_sql = ""
        if date_range:
            date_range_sql = "AND date(consumed_on) BETWEEN ? AND ?"

        sql = ""
        placeholders: PlaceholderTuple = ()
        if date_range and query:
            sql = f"""SELECT f.id, f.foods_eaten, f.overate,
            f.consumed_on as 'consumed_on [local_datetime]'
            FROM foodlog AS f, foodlog_fts
            WHERE f.id=foodlog_fts.rowid
            AND foodlog_fts MATCH ?
            {date_range_sql}
            ORDER BY f.consumed_on DESC
            LIMIT ? OFFSET ?"""

            placeholders = (query.strip(),) + date_range + (limit, offset)

        if date_range and not query:
            sql = f"""SELECT f.id, f.foods_eaten, f.overate,
            f.consumed_on as 'consumed_on [local_datetime]'
            FROM foodlog AS f
            WHERE 1=1
            {date_range_sql}
            ORDER BY f.consumed_on DESC
            LIMIT ? OFFSET ?"""

            placeholders = date_range + (limit, offset)

        if query and not date_range:
            sql = """SELECT f.id, f.foods_eaten, f.overate,
            f.consumed_on as 'consumed_on [local_datetime]'
            FROM foodlog AS f, foodlog_fts
            WHERE f.id=foodlog_fts.rowid
            AND foodlog_fts MATCH ?
            ORDER BY f.consumed_on DESC
            LIMIT ? OFFSET ?"""

            placeholders = (query.strip(), limit, offset)

        if not sql:
            sql = """SELECT f.id, f.foods_eaten, f.overate,
            f.consumed_on as 'consumed_on [local_datetime]'
            FROM foodlog AS f
            ORDER BY f.consumed_on DESC
            LIMIT ? OFFSET ?"""
            placeholders = (limit, offset)

        return (
            self._select_generator(sql, placeholders),
            self._count(sql, placeholders)
        )

    def upsert(
            self,
            entry_id: int,
            **kwargs: Any
    ) -> int:
        """Insert or update an entry."""

        consumed_on = kwargs.get("consumed_on")
        foods_eaten = kwargs.get("foods_eaten")
        overate = int(kwargs.get("overate", 0))

        if entry_id == 0:
            upsert_id = self._insert(
                """INSERT INTO foodlog (consumed_on, foods_eaten, overate)
                VALUES (?, ?, ?)""",
                (consumed_on, foods_eaten, overate)
            )

        if entry_id > 0:
            self._execute(
                """UPDATE foodlog SET consumed_on=?, foods_eaten=?, overate=?
                WHERE id=?""",
                (consumed_on, foods_eaten, overate, entry_id)
            )
            upsert_id = entry_id

        return upsert_id
