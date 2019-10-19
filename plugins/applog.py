"""Capture log messages to an Sqlite database."""

from collections import deque
import sqlite3
from typing import List, Optional, Sequence, Tuple, Union
import cherrypy
from cherrypy.process import plugins, wspbus
from . import mixins
from . import decorators


class Plugin(plugins.SimplePlugin, mixins.Sqlite):
    """A CherryPy plugin for storing application-centric log messages."""

    def __init__(self, bus: wspbus.Bus) -> None:
        plugins.SimplePlugin.__init__(self, bus)
        self.db_path = self._path("applog.sqlite")
        self.queue: deque = deque()

        self._create("""
        PRAGMA journal_mode=WAL;

        CREATE TABLE IF NOT EXISTS applog (
            created DEFAULT(strftime('%Y-%m-%d %H:%M:%f', 'now')),
            source VARCHAR(255) NOT NULL,
            key VARCHAR(255) NOT NULL,
            value VARCHAR(255) NOT NULL
        );

        CREATE INDEX IF NOT EXISTS index_source
            ON applog(source);

        CREATE INDEX IF NOT EXISTS index_created_today
            ON applog(date(created));

        """)

    def start(self) -> None:
        """Define the CherryPy messages to listen for.

        This plugin owns the applog prefix.
        """
        self.bus.subscribe("applog:add", self.add)
        self.bus.subscribe("applog:process_queue", self.process_queue)
        self.bus.subscribe("applog:get_newest", self.get_newest)
        self.bus.subscribe("applog:prune", self.prune)
        self.bus.subscribe("applog:search", self.search)

    def get_newest(self, source: str, key: str) -> Optional[sqlite3.Row]:
        """Retrieve messages by key."""

        return self._selectFirst(
            """SELECT value FROM applog
            WHERE source=? AND key=? ORDER BY rowid DESC LIMIT 1""",
            (source, key)
        )

    def process_queue(self) -> None:
        """Transfer messages from the queue to the database."""

        messages = list(self.queue)

        if not messages:
            return

        # Only remove as many elements as were read in case more
        # have just been added.
        for _ in range(len(messages)):
            self.queue.popleft()

        self._insert(
            "INSERT INTO applog (source, key, value) VALUES (?, ?, ?)",
            messages
        )

    def add(self,
            caller: str,
            key: str,
            value: Union[str, float, int]) -> None:
        """Accept a log message for storage."""

        self.queue.append((caller, key, str(value)))

        cherrypy.engine.publish("scheduler:add", 1, "applog:process_queue")

        # Mirror the log message on the cherrypy log for convenience.
        cherrypy.log(f"{caller}: {value}")

    @decorators.log_runtime
    def prune(self, cutoff_months: int = 3) -> None:
        """Delete old records.

        This is normally invoked from the maintenance plugin, and
        keeps the applog database from unlimited growth. The
        likelihood of very old applog records being needed or wanted
        is low.

        """

        deletion_count = self._delete(
            """DELETE FROM applog
            WHERE strftime('%s', created) < strftime('%s', 'now', ?)
            """,
            (f"-{cutoff_months} month",)
        )

        cherrypy.engine.publish(
            "applog:add",
            "applog",
            "prune",
            f"pruned {deletion_count} records"
        )

    @decorators.log_runtime
    def search(self,
               sources: Sequence[str] = (),
               offset: int = 0,
               limit: int = 20,
               exclude: int = 0) -> Tuple[List[sqlite3.Row], int, sqlite3.Row]:
        """View records in reverse chronological order."""

        where_sql = "WHERE 1=1"
        placeholder_values: Tuple[str, ...] = ()

        if sources:
            placeholders = ("?, " * len(sources))[:-2]
            if exclude == 1:
                where_sql += f" AND source NOT IN ({placeholders})"
            else:
                where_sql += f" AND source IN ({placeholders})"

            placeholder_values += tuple(sources)

        if not sources:
            where_sql += " AND date(created) = date('now')"

        sql = f"""SELECT key, value, source,
        created as 'created [datetime]'
        FROM applog
        {where_sql}
        ORDER BY rowid DESC
        LIMIT ? OFFSET ?"""

        placeholder_values += (limit, offset)

        return (
            self._select(sql, placeholder_values),
            self._count(sql, placeholder_values),
            self._explain(sql, placeholder_values)
        )
