"""Perform maintenance tasks."""

import gc
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

        cherrypy.engine.publish(
            "applog:add",
            "maintenance",
            "Finished database maintenance"
        )
