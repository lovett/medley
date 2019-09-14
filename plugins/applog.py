"""Capture log messages to an Sqlite database."""

import cherrypy
from . import mixins
from . import decorators


class Plugin(cherrypy.process.plugins.SimplePlugin, mixins.Sqlite):
    """A CherryPy plugin for storing application-centric log messages."""

    def __init__(self, bus):
        cherrypy.process.plugins.SimplePlugin.__init__(self, bus)

        self.db_path = self._path("applog.sqlite")

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

        """, keep_connection_open=True)

    def start(self):
        """Define the CherryPy messages to listen for.

        This plugin owns the applog prefix.
        """
        self.bus.subscribe("applog:add", self.add)
        self.bus.subscribe("applog:get_newest", self.get_newest)
        self.bus.subscribe("applog:prune", self.prune)
        self.bus.subscribe("applog:search", self.search)

    def get_newest(self, source, key):
        """Retrieve messages by key."""

        return self._selectFirst(
            """SELECT value FROM applog
            WHERE source=? AND key=? ORDER BY rowid DESC LIMIT 1""",
            (source, key)
        )

    def add(self, caller, key, value):
        """Accept a log message for storage."""

        try:
            source = caller.__module__
        except AttributeError:
            source = caller

        self._insert(
            "INSERT INTO applog (source, key, value) VALUES (?, ?, ?)",
            [(source, key, str(value))]
        )

        # Mirror the log message on the cherrypy log for convenience.
        cherrypy.log(f"{source}: {value}")

    @decorators.log_runtime
    def prune(self, cutoff_months=6):
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
    def search(self, sources=(), offset=0, limit=20, exclude=0):
        """View records in reverse chronological order."""

        where_sql = "WHERE 1=1"
        placeholder_values = ()

        if sources:
            placeholders = ("?, " * len(sources))[:-2]
            if exclude == 1:
                where_sql += f" AND source NOT IN ({placeholders})"
            else:
                where_sql += f" AND source IN ({placeholders})"

            placeholder_values += tuple(sources)

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
