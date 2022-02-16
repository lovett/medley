"""Storage for food log entries."""

import sqlite3
from typing import Any
from typing import Iterator
from typing import Optional
from typing import Tuple
from typing import cast
import cherrypy
from plugins import mixins
from plugins import decorators

SearchResult = Tuple[
    Iterator[sqlite3.Row], int
]


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
        AFTER UPDATE OF foods_eated ON foodlog
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
        self.bus.subscribe("foodlog:remove", self.remove)
        self.bus.subscribe("foodlog:search:date", self.search_by_date)
        self.bus.subscribe("foodlog:search:keyword", self.search_by_keyword)
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

    def search_by_date(self, **kwargs: Any) -> SearchResult:
        """Locate entries that match a date search."""

        query = kwargs.get("query", "")
        limit = int(kwargs.get("limit", 20))
        offset = int(kwargs.get("offset", 0))

        consumed_on = ""
        where_clause = ""
        if query:
            consumed_on = cherrypy.engine.publish(
                "clock:format",
                query,
                "%Y-%m-%d"
            ).pop()

            where_clause = "WHERE date(consumed_on) = ?"

        sql = f"""SELECT id, foods_eaten, overate,
        consumed_on as 'consumed_on [local_datetime]'
        FROM foodlog
        {where_clause}
        ORDER BY consumed_on DESC
        LIMIT ? OFFSET ?"""

        placeholders = cast(Any, (limit, offset))
        if query:
            placeholders = (consumed_on, limit, offset)

        return (
            self._select_generator(sql, placeholders),
            self._count(sql, placeholders)
        )

    def search_by_keyword(self, **kwargs: Any) -> SearchResult:
        """Locate entries that match a keyword search."""

        limit = int(kwargs.get("limit", 20))
        offset = int(kwargs.get("offset", 20))
        query = kwargs.get("query", "")

        sql = """SELECT f.id, f.foods_eaten, f.overate,
        f.consumed_on as 'consumed_on [local_datetime]'
        FROM foodlog AS f, foodlog_fts
        WHERE f.id=foodlog_fts.rowid
        AND foodlog_fts MATCH ?
        ORDER BY f.consumed_on DESC
        LIMIT ? OFFSET ?"""

        placeholders = (query, limit, offset)
        return (
            self._select_generator(sql, placeholders),
            self._count(sql, placeholders)
        )

    def upsert(
            self,
            entry_id: int,
            **kwargs: Any
    ) -> bool:
        """Insert or update an entry."""

        consumed_on = kwargs.get("consumed_on")
        foods_eaten = kwargs.get("foods_eaten")
        overate = int(kwargs.get("overate", 0))

        if entry_id == 0:
            return self._execute(
                """INSERT INTO foodlog (consumed_on, foods_eaten, overate)
                VALUES (?, ?, ?)""",
                (consumed_on, foods_eaten, overate)
            )

        return self._execute(
            """UPDATE foodlog SET consumed_on=?, foods_eaten=?, overate=?
            WHERE id=?""",
            (consumed_on, foods_eaten, overate, entry_id)
        )
