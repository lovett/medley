"""Perform maintenance tasks."""

import gc
import glob
import os
import os.path
import time
import cherrypy
from plugins import mixins
from plugins import decorators


class Plugin(cherrypy.process.plugins.SimplePlugin, mixins.Sqlite):
    """A CherryPy plugin for executing maintenance tasks."""

    def __init__(self, bus: cherrypy.process.wspbus.Bus) -> None:
        cherrypy.process.plugins.SimplePlugin.__init__(self, bus)

    def start(self) -> None:
        """Define the CherryPy messages to listen for.

        This plugin owns the maintenance prefix.
        """
        self.bus.subscribe("maintenance", self.maintenance)

    def maintenance(self) -> None:
        """Entry point for all maintenance tasks."""

        self.db_maintenance()

        # Might as well garbage collect since we're in a maintenance
        # frame of mind. No particular expectation that doing so will
        # have a noticeable impact or is especially necessary. Even
        # so, why not.
        gc.collect()

        cherrypy.engine.publish(
            "applog:add",
            "maintenance",
            "Ran garbage collection"
        )

    @decorators.log_runtime
    def db_maintenance(self) -> None:
        """Execute database maintenance tasks."""

        cherrypy.engine.publish(
            "applog:add",
            "maintenance",
            "Starting database maintenance"
        )

        cherrypy.engine.publish("applog:prune")
        cherrypy.engine.publish("bookmarks:prune")
        cherrypy.engine.publish("cache:prune")
        cherrypy.engine.publish("capture:prune")
        cherrypy.engine.publish("metrics:prune")
        cherrypy.engine.publish("recipes:prune")

        cherrypy.engine.publish("bookmarks:repair")
        cherrypy.engine.publish("logindex:repair")

        file_paths = glob.glob(self._path("*.sqlite"), recursive=False)

        for file_path in file_paths:
            stat = os.stat(file_path)
            age = time.time() - stat.st_mtime
            name = os.path.basename(file_path)

            # Databases that haven't changed in the past 24 hours
            # don't need maintenance.
            if age > 86400:
                cherrypy.engine.publish(
                    "applog:add",
                    "maintenance",
                    f"Skipped {name}"
                )

                continue

            self.db_path = file_path
            self._execute("vacuum")
            self._execute("analyze")
            self._execute("PRAGMA wal_checkpoint(TRUNCATE)")

            cherrypy.engine.publish(
                "applog:add",
                "maintenance",
                f"Finished {name}"
            )

        cherrypy.engine.publish(
            "applog:add",
            "maintenance",
            "Finished database maintenance"
        )
