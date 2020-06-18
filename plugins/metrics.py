"""Storage for performance measurements."""

from collections import deque
import sqlite3
import typing
import cherrypy
from plugins import mixins
from plugins import decorators


class Plugin(cherrypy.process.plugins.SimplePlugin, mixins.Sqlite):
    """A CherryPy plugin for storing performance measurements."""

    def __init__(self, bus: cherrypy.process.wspbus.Bus) -> None:
        cherrypy.process.plugins.SimplePlugin.__init__(self, bus)
        self.db_path = self._path("metrics.sqlite")
        self.queue: deque = deque()

        self._create("""
        PRAGMA journal_mode=WAL;

        CREATE TABLE IF NOT EXISTS metrics (
            created DEFAULT(strftime('%Y-%m-%d %H:%M:%f', 'now')),
            key VARCHAR(255) NOT NULL,
            value INTEGER NOT NULL,
            unit VARCHAR(255) NOT NULL
        );

        CREATE INDEX IF NOT EXISTS index_key
            ON metrics(key);

        CREATE INDEX IF NOT EXISTS index_created
            ON metrics(date(created));

        CREATE VIEW IF NOT EXISTS today AS
            SELECT rowid, key, value, unit, created
            FROM metrics
            WHERE date('now') = date(created);

        """)

    def start(self) -> None:
        """Define the CherryPy messages to listen for.

        This plugin owns the metrics prefix.
        """
        self.bus.subscribe("metrics:add", self.add)
        self.bus.subscribe("metrics:inventory", self.inventory)
        self.bus.subscribe("metrics:pull", self.pull)
        self.bus.subscribe("metrics:prune", self.prune)
        self.bus.subscribe("metrics:dataset", self.dataset)

    def pull(self) -> None:
        """Transfer messages from the queue to the database."""

        messages = list(self.queue)

        if not messages:
            return

        # Only remove as many elements as were read in case more
        # have just been added.
        for _ in range(len(messages)):
            self.queue.popleft()

        self._multi([
            ("INSERT INTO metrics (key, value, unit) VALUES (?, ?, ?)",
             message)
            for message in messages
        ])

    def add(self, key: str, value: float, unit: str) -> None:
        """Accept a message for storage."""

        self.queue.append((key, value, unit))

        cherrypy.engine.publish("scheduler:add", 1, "metrics:pull")

    @decorators.log_runtime
    def inventory(self) -> typing.Iterator[sqlite3.Row]:
        """List all available metrics."""

        return self._select_generator(
            """SELECT DISTINCT key
            FROM metrics
            GROUP BY key HAVING count(*) > 1
            ORDER BY key"""
        )

    @decorators.log_runtime
    def prune(self, cutoff_months: int = 6) -> None:
        """Delete old records to keep database size reasonable.

        This is normally invoked from the maintenance plugin.

        """

        self._delete(
            """DELETE FROM metrics
            WHERE strftime('%s', created) < strftime('%s', 'now', ?)
            """,
            (f"-{cutoff_months} month",)
        )

    @decorators.log_runtime
    def dataset(self, key: str, view: str) -> typing.Iterator[sqlite3.Row]:
        """Retrieve records for a single metric."""

        return self._select_generator(
            f"""SELECT created as 'created [timestamp]', value, unit
            FROM {view}
            WHERE key=?
            ORDER BY created""",
            (key,)
        )
