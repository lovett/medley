import sqlite3
import cherrypy
import os
from cherrypy.process import plugins

class Plugin(plugins.SimplePlugin):

    def __init__(self, bus):
        plugins.SimplePlugin.__init__(self, bus)

    def start(self):
        with self.connect() as con:
            con.executescript(
                """CREATE TABLE IF NOT EXISTS logs (
                created DEFAULT CURRENT_TIMESTAMP,
                source VARCHAR(255) NOT NULL,
                event VARCHAR(255) NOT NULL,
                value VARCHAR(255) NOT NULL)"""
            )

        self.bus.subscribe('app-log', self.log_event)


    def stop(self):
        pass

    def connect(self):
        path = os.path.join(
            cherrypy.config.get("database_dir"),
            "logs.sqlite"
        )
        con = sqlite3.connect(path, detect_types=sqlite3.PARSE_COLNAMES)
        con.row_factory = sqlite3.Row
        return con

    def log_event(self, source, event, value):
        with self.connect() as con:
            con.execute(
                "INSERT INTO logs (source, event, value) VALUES (?, ?, ?)",
                (source, event, value)
            )
