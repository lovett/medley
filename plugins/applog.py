"""Capture log messages to an Sqlite database."""

import cherrypy
from . import mixins


class Plugin(cherrypy.process.plugins.SimplePlugin, mixins.Sqlite):
    """A CherryPy plugin for storing application-centric log messages."""

    def __init__(self, bus):
        cherrypy.process.plugins.SimplePlugin.__init__(self, bus)

        self.db_path = self._path("applog.sqlite")

        self._create("""
        CREATE TABLE IF NOT EXISTS applog (
            created DEFAULT(strftime('%Y-%m-%d %H:%M:%f', 'now')),
            source VARCHAR(255) NOT NULL,
            key VARCHAR(255) NOT NULL,
            value VARCHAR(255) NOT NULL
        );
        CREATE INDEX IF NOT EXISTS index_source ON applog(source);
        """)

    def start(self):
        """Define the CherryPy messages to listen for.

        This plugin owns the applog prefix.
        """
        self.bus.subscribe("applog:add", self.add)
        self.bus.subscribe("applog:get_newest", self.get_newest)
        self.bus.subscribe("applog:prune", self.prune)

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
        cherrypy.log("{}: {}".format(
            source,
            value
        ))

    def prune(self, cutoff_months=6):
        """Delete old records.

        This is normally invoked from the maintenance plugin, and
        keeps the applog database from unlimited growth. The
        likelihood of very old applog records being needed or wanted
        is low.

        """

        cutoff_months = int(cutoff_months) * -1

        deletion_count = self._delete(
            """DELETE FROM applog
            WHERE strftime('%s', created) < strftime('%s', 'now', '{} month')
            """.format(cutoff_months)
        )

        cherrypy.engine.publish(
            "applog:add",
            "applog",
            "prune",
            "pruned {} records".format(deletion_count)
        )
