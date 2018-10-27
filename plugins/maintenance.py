"""Perform maintenance tasks."""

import glob
import cherrypy
from cherrypy.process import plugins
from . import mixins
from . import decorators


class Plugin(plugins.SimplePlugin, mixins.Sqlite):
    """A CherryPy plugin for executing maintenance tasks."""

    def __init__(self, bus):
        plugins.SimplePlugin.__init__(self, bus)

    def start(self):
        """Define the CherryPy messages to listen for.

        This plugin owns the maintenance prefix.
        """
        self.bus.subscribe("maintenance:db", self.db_maintenance)
        self.bus.subscribe("maintenance:filesystem", self.fs_maintenance)

    @decorators.log_runtime
    def db_maintenance(self, file_names=None):
        """Execute database maintenance tasks."""

        cherrypy.engine.publish("cache:prune")
        cherrypy.engine.publish("applog:prune")

        pattern = self._path("*.sqlite")
        file_names = glob.glob(pattern, recursive=False)

        for file_name in file_names:
            self.db_path = file_name
            self._execute("vacuum")
            self._execute("analyze")

    @staticmethod
    @decorators.log_runtime
    def fs_maintenance():
        """Execute filesystem maintenance tasks."""

        cherrypy.engine.publish("speak:prune")
