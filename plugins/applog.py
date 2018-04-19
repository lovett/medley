import cherrypy
from . import mixins


class Plugin(cherrypy.process.plugins.SimplePlugin, mixins.Sqlite):

    def __init__(self, bus):
        cherrypy.process.plugins.SimplePlugin.__init__(self, bus)

        self.db_path = self._path("applog.sqlite")

        self._create("""
        CREATE TABLE IF NOT EXISTS applog (
            created DEFAULT(strftime('%Y-%m-%d %H:%M:%f', 'NOW')),
            source VARCHAR(255) NOT NULL,
            key VARCHAR(255) NOT NULL,
            value VARCHAR(255) NOT NULL
        );
        CREATE INDEX IF NOT EXISTS index_source ON applog(source);
        """)

    def start(self):
        self.bus.subscribe("applog:add", self.add)

    def stop(self):
        pass

    def add(self, caller, key, value):
        try:
            source = caller.__module__
        except AttributeError:
            source = caller

        self._insert(
            "INSERT INTO applog (source, key, value) VALUES (?, ?, ?)",
            [(source, key, value)]
        )

        # Also write a message to the application log for convenience.
        cherrypy.log("{}: {}".format(
            source,
            value
        ))
