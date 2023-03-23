"""Storage for sleep tracking."""

import sqlite3
from typing import Any
from typing import List
from typing import Optional
from typing import Tuple
import cherrypy
from plugins import mixins
from plugins import decorators

SearchResult = Tuple[
    List[sqlite3.Row], int
]


class Plugin(cherrypy.process.plugins.SimplePlugin, mixins.Sqlite):
    """Store sleep logs via SQLite."""

    def __init__(self, bus: cherrypy.process.wspbus.Bus) -> None:
        cherrypy.process.plugins.SimplePlugin.__init__(self, bus)

        self.db_path = self._path("sleeplog.sqlite")

    def setup(self) -> None:
        """Create the database."""

        self._create("""
        PRAGMA journal_mode=WAL;
        PRAGMA foreign_keys=ON;

        CREATE TABLE IF NOT EXISTS sleeplog (
            id INTEGER PRIMARY KEY,
            start_utc TEXT,
            end_utc TEXT DEFAULT NULL,
            duration_seconds INT,
            notes TEXT DEFAULT NULL
        );

        CREATE VIRTUAL TABLE IF NOT EXISTS sleeplog_fts USING fts5 (
            notes,
            content=sleeplog,
            tokenize=porter
        );

        CREATE TRIGGER IF NOT EXISTS sleeplog_after_insert
        AFTER INSERT ON sleeplog
        BEGIN
        INSERT INTO sleeplog_fts (rowid, notes)
        VALUES (new.rowid, new.notes);

        UPDATE sleeplog SET duration_seconds=IFNULL(
          strftime('%s', new.end_utc) - strftime('%s', new.start_utc),
          0) WHERE sleeplog.rowid=new.rowid;
        END;

        CREATE TRIGGER IF NOT EXISTS sleeplog_after_update
        AFTER UPDATE ON sleeplog
        BEGIN
        INSERT INTO sleeplog_fts (sleeplog_fts, rowid, notes)
            VALUES ('delete', old.rowid, old.notes);
        INSERT INTO sleeplog_fts (rowid, notes)
            VALUES (new.rowid, new.notes);
        UPDATE sleeplog SET duration_seconds=IFNULL(
          (strftime('%s', new.end_utc) - strftime('%s', new.start_utc)),
          0) WHERE sleeplog.rowid=new.rowid;
        END;

        CREATE TRIGGER IF NOT EXISTS sleeplog_after_delete
        AFTER DELETE ON sleeplog
        BEGIN
        INSERT INTO sleeplog_fts(sleeplog_fts, rowid, notes)
            VALUES ('delete', old.rowid, old.notes);
        END;

        """)

    def start(self) -> None:
        """Define the CherryPy messages to listen for.

        This plugin owns the sleeplog prefix.
        """

        self.bus.subscribe("server:ready", self.setup)
        self.bus.subscribe("sleeplog:find", self.find)
        self.bus.subscribe("sleeplog:start", self.start_session)
        self.bus.subscribe("sleeplog:end", self.end_session)
        self.bus.subscribe("sleeplog:remove", self.remove)
        self.bus.subscribe("sleeplog:active", self.active_session)
        self.bus.subscribe("sleeplog:history", self.history)
        self.bus.subscribe("sleeplog:upsert", self.upsert)
        self.bus.subscribe("sleeplog:search:keyword", self.search_by_keyword)
        self.bus.subscribe("sleeplog:search:date", self.search_by_date)

    def find(self, entry_id: int) -> Optional[sqlite3.Row]:
        """Locate an entry by its ID."""

        return self._selectOne(
            """SELECT id, start_utc as 'start [local_datetime]',
            end_utc as 'end [local_datetime]', notes
            FROM sleeplog
            WHERE id=?""",
            (entry_id,)
        )

    @decorators.log_runtime
    def remove(self, entry_id: int) -> bool:
        """Delete an entry."""

        return self._execute(
            "DELETE FROM sleeplog WHERE id=?",
            (entry_id,)
        )

    def active_session(self) -> Optional[sqlite3.Row]:
        """The first sleep record with a start date but not an end date."""

        sql = """SELECT id, start_utc as 'start [local_datetime]', notes
        FROM sleeplog
        WHERE end_utc IS NULL
        LIMIT 1"""

        return self._selectOne(sql)

    def search_by_date(self, **kwargs: Any) -> SearchResult:
        """Sessions by reverse-chronological date."""

        limit = int(kwargs.get("limit", 20))
        offset = int(kwargs.get("offset", 0))
        (ideal_min, ideal_max) = [
            val * 3600
            for val in kwargs.get("ideal_duration", [])
        ]

        ideal_sql = ""
        if ideal_min and ideal_max:
            ideal_sql += f"""
            , IIF({ideal_min} - duration_seconds > 0,
                  {ideal_min} - duration_seconds,
                  0) as 'deficit [duration]'
            , IIF(duration_seconds - {ideal_max} > 0,
                duration_seconds - {ideal_max},
                0) as 'surplus [duration]'"""

        sql = f"""SELECT id, start_utc as 'start [local_datetime]',
        end_utc as 'end [local_datetime]',
        duration_seconds AS 'duration [duration]',
        notes {ideal_sql}
        FROM sleeplog
        WHERE end_utc IS NOT NULL
        ORDER BY end_utc DESC
        LIMIT ? OFFSET ?"""

        placeholders = (limit, offset)

        return (
            self._select(sql, placeholders),
            self._count(sql, placeholders)
        )

    def search_by_keyword(self, **kwargs: Any) -> SearchResult:
        """Locate entries with notes that match a keyword search."""

        limit = int(kwargs.get("limit", 20))
        offset = int(kwargs.get("offset", 0))
        query = kwargs.get("query", "")
        (ideal_min, ideal_max) = [
            val * 3600
            for val in kwargs.get("ideal_duration", [])
        ]

        ideal_sql = ""
        if ideal_min and ideal_max:
            ideal_sql += f"""
            , IIF({ideal_min} - s.duration_seconds > 0,
                  {ideal_min} - s.duration_seconds,
                  0) as 'deficit [duration]'
            , IIF(s.duration_seconds - {ideal_max} > 0,
                s.duration_seconds - {ideal_max},
                0) as 'surplus [duration]'"""

        sql = f"""SELECT s.id, s.start_utc as 'start [local_datetime]',
        end_utc as 'end [local_datetime]',
        duration_seconds AS 'duration [duration]',
        s.notes {ideal_sql}
        FROM sleeplog AS s, sleeplog_fts
        WHERE s.id=sleeplog_fts.rowid
        AND sleeplog_fts MATCH ?
        ORDER BY s.end_utc DESC
        LIMIT ? OFFSET ?"""

        placeholders = (query, limit, offset)
        return (
            self._select(sql, placeholders),
            self._count(sql, placeholders)
        )

    def history(self, days: int) -> List[sqlite3.Row]:
        """Total duration by day for the past n days."""

        sql = """WITH RECURSIVE calendar(days_ago, dt) AS
        (SELECT 1, date('now', '-1 day')
        UNION ALL SELECT days_ago+1, date(dt, '-1 day')
        FROM calendar LIMIT ?)
        SELECT days_ago, dt as 'date [date]',
        SUM(COALESCE(duration_seconds / 3600.0, 0)) as hours
        FROM calendar
        LEFT JOIN sleeplog ON date(start_utc)=dt
        AND end_utc IS NOT NULL
        GROUP BY dt
        ORDER BY dt"""

        placeholders = (days,)

        return self._select(sql, placeholders)

    def start_session(self) -> None:
        """Create a new session based on the current time."""

        self._execute(
            """INSERT INTO sleeplog (start_utc)
            VALUES (datetime('now'))"""
        )

    def end_session(self, uid: int) -> None:
        """End an active session."""

        self._execute(
            """UPDATE sleeplog
            SET end_utc=datetime('now')
            WHERE id=?""",
            (uid,)
        )

    def upsert(
            self,
            entry_id: int,
            **kwargs: Any
    ) -> int:
        """Insert or update an entry."""

        start_utc = kwargs.get("start_utc")
        end_utc = kwargs.get("end_utc")
        notes = kwargs.get("notes")

        if entry_id == 0:
            upsert_id = self._insert(
                """INSERT INTO sleeplog (start_utc, end_utc, notes)
                VALUES (datetime(?), datetime(?), ?)""",
                (start_utc, end_utc, notes)
            )

        if entry_id > 0:
            self._execute(
                """UPDATE sleeplog SET start_utc=datetime(?),
                end_utc=datetime(?),
                notes=?
                WHERE id=?""",
                (start_utc, end_utc, notes, entry_id)
            )
            upsert_id = entry_id

        return upsert_id
