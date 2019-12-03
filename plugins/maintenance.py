"""Perform maintenance tasks."""

import glob
import os
import time
import typing
import cherrypy
from . import mixins
from . import decorators


class Plugin(cherrypy.process.plugins.SimplePlugin, mixins.Sqlite):
    """A CherryPy plugin for executing maintenance tasks."""

    def __init__(self, bus: cherrypy.process.wspbus.Bus) -> None:
        cherrypy.process.plugins.SimplePlugin.__init__(self, bus)

    def start(self) -> None:
        """Define the CherryPy messages to listen for.

        This plugin owns the maintenance prefix.
        """
        self.bus.subscribe("maintenance:db", self.db_maintenance)

    @decorators.log_runtime
    def db_maintenance(
            self,
            file_names: typing.Optional[typing.Sequence[str]] = ()
    ) -> None:
        """Execute database maintenance tasks."""

        cherrypy.engine.publish("cache:prune")
        cherrypy.engine.publish("applog:prune")
        cherrypy.engine.publish("bookmarks:prune")
        cherrypy.engine.publish("bookmarks:repair")
        cherrypy.engine.publish("logindex:repair")

        pattern = self._path("*.sqlite")
        file_names = glob.glob(pattern, recursive=False)

        for file_name in file_names:
            # Skip databases that haven't been changed in the past 24 hours.
            stat = os.stat(file_name)
            age = time.time() - stat.st_mtime
            if age > 86400:
                cherrypy.engine.publish(
                    "applog:add",
                    "maintenance",
                    "db:skip",
                    file_name
                )

                continue

            self.db_path = file_name
            self._execute("vacuum")
            self._execute("analyze")
            self._execute("PRAGMA wal_checkpoint(TRUNCATE)")
            cherrypy.engine.publish(
                "applog:add",
                "maintenance",
                f"db:{self.db_path}",
                "ok"
            )
