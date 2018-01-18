import cherrypy
from . import mixins

class Plugin(cherrypy.process.plugins.SimplePlugin, mixins.Sqlite):

    def __init__(self, bus):
        cherrypy.process.plugins.SimplePlugin.__init__(self, bus)

        self.db_path = self._path("applog.sqlite")

        self._create("""CREATE TABLE IF NOT EXISTS applog (
                created DEFAULT CURRENT_TIMESTAMP,
                source VARCHAR(255) NOT NULL,
                key VARCHAR(255) NOT NULL,
                value VARCHAR(255) NOT NULL)""")

    def start(self):
        self.bus.subscribe('applog', self.add)


    def stop(self):
        pass

    def add(self, source, key, value):
        return self._insert(
            "INSERT INTO logs (source, key, value) VALUES (?, ?, ?)",
            (source, key, value)
        )
