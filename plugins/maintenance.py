"""Perform maintenance tasks."""

import glob
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

    @decorators.log_runtime
    def db_maintenance(self, file_names=None):
        """Run the SQLite vacuum and analyze commands on each known
        database.

        """

        if file_names is None:
            pattern = self._path("*.sqlite")
            file_names = glob.glob(pattern, recursive=False)
        if not file_names:
            return

        self.db_path = file_names[0]
        self._execute("vacuum")
        self._execute("analyze")

        self.db_maintenance(file_names[1:])
