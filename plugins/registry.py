import cherrypy
from . import mixins

class Plugin(cherrypy.process.plugins.SimplePlugin, mixins.Sqlite):

    def __init__(self, bus):
        cherrypy.process.plugins.SimplePlugin.__init__(self, bus)

        self.db_path = self._path("registry.sqlite")

        self._registerConverters()

        self._create("""CREATE TABLE IF NOT EXISTS registry (
            key VARCHAR(255) NOT NULL,
            value VARCHAR(255),
            created DEFAULT CURRENT_TIMESTAMP)""")

    def start(self):
        self.bus.subscribe("registry:remove", self.remove)
        self.bus.subscribe("registry:add", self.add)
        self.bus.subscribe("registry:add_many", self.addMany)

    def stop(self):
        pass

    def add(self, key, value, replace=False):
        self.addMany(key, [value], replace)

    def addMany(self, key, values=[], replace=False):
        if replace:
            self.remove(key)

        placeholder_values = [(key, value) for value in values]

        self._insertMany("INSERT INTO registry (key, value) VALUES (?, ?)", placeholder_values)

    def remove(self, key):
        deletions = self._delete("DELETE FROM registry WHERE key=?", (key,))
        cherrypy.engine.publish("app-log", "registry", "clear_key:{}".format(key), deletions)
        return deletions
