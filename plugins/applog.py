"""Storage for log messages."""

from collections import deque
import sqlite3
import typing
import cherrypy
from plugins import mixins
from plugins import decorators

SearchResult = typing.Tuple[
    typing.List[sqlite3.Row], int, typing.List[str]
]


class Plugin(cherrypy.process.plugins.SimplePlugin, mixins.Sqlite):
    """A CherryPy plugin for storing log messages."""

    def __init__(self, bus: cherrypy.process.wspbus.Bus) -> None:
        cherrypy.process.plugins.SimplePlugin.__init__(self, bus)
        self.db_path = self._path("applog.sqlite")
        self.queue: deque = deque()

        self._create("""
        PRAGMA journal_mode=WAL;

        CREATE TABLE IF NOT EXISTS applog (
            created DEFAULT(strftime('%Y-%m-%d %H:%M:%f', 'now', 'localtime')),
            source VARCHAR(255) NOT NULL,
            message VARCHAR(255) NOT NULL
        );

        CREATE INDEX IF NOT EXISTS index_source
            ON applog(source);

        CREATE INDEX IF NOT EXISTS index_created
            ON applog(date(created));

        """)

    def start(self) -> None:
        """Define the CherryPy messages to listen for.

        This plugin owns the applog prefix.
        """
        self.bus.subscribe("applog:add", self.add)
        self.bus.subscribe("applog:pull", self.pull)
        self.bus.subscribe("applog:newest", self.newest)
        self.bus.subscribe("applog:prune", self.prune)
        self.bus.subscribe("applog:search", self.search)
        self.bus.subscribe("applog:sources", self.list_sources)
        self.bus.subscribe("applog:view", self.view)

    def newest(
            self,
            source: str
    ) -> typing.Optional[str]:
        """Retrieve messages by key."""

        return typing.cast(
            typing.Optional[str],
            self._selectFirst(
                """SELECT message FROM applog
                WHERE source=? ORDER BY created DESC LIMIT 1""",
                (source,)
            )
        )

    def pull(self) -> None:
        """Transfer messages from the queue to the database."""

        messages = list(self.queue)

        if not messages:
            return

        # Only remove as many elements as were read in case more
        # have just been added.
        for _ in range(len(messages)):
            self.queue.popleft()

        queries = [
            ("INSERT INTO applog (source, message) VALUES (?, ?)",
             message)
            for message in messages
        ]

        self._multi(queries)

    def add(self, source: str, message: typing.Any) -> None:
        """Accept a log message for storage."""

        self.queue.append((
            source,
            str(message)
        ))

        cherrypy.engine.publish("scheduler:add", 1, "applog:pull")

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
            WHERE strftime('%s', created) < strftime('%s', 'now', ?)""",
            (f"-{cutoff_months} month",)
        )

        unit = "row" if deletion_count == 1 else "rows"

        cherrypy.engine.publish(
            "applog:add",
            "applog:prune",
            f"{deletion_count} {unit} deleted"
        )

    @decorators.log_runtime
    def view(self, **kwargs: typing.Any) -> SearchResult:
        """View records in reverse chronological order."""

        offset: int = kwargs.get("offset", 0)
        limit: int = kwargs.get("limit", 0)

        sql = """SELECT source, message,
        created as 'created [timestamp]'
        FROM applog
        ORDER BY created DESC, rowid desc
        LIMIT ? OFFSET ?"""

        placeholders = (limit, offset)

        return (
            self._select(sql, placeholders),
            self._count(sql, placeholders),
            self._explain(sql, placeholders)
        )

    @decorators.log_runtime
    def search(self, source: str, **kwargs: typing.Any) -> SearchResult:
        """View records from a source in reverse chronological order."""

        offset: int = kwargs.get("offset", 0)
        limit: int = kwargs.get("limit", 0)

        sql = """SELECT source, message,
        created as 'created [timestamp]'
        FROM applog
        WHERE source=?
        ORDER BY created DESC
        LIMIT ? OFFSET ?"""

        placeholders = (source, limit, offset)

        return (
            self._select(sql, placeholders),
            self._count(sql, placeholders),
            self._explain(sql, placeholders)
        )

    def list_sources(self) -> typing.Iterator[sqlite3.Row]:
        """List all available sources."""

        sql = """SELECT distinct source
        FROM applog
        ORDER BY source"""

        return self._select_generator(sql)
