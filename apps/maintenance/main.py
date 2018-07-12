"""Perform maintenance tasks."""

import cherrypy


class Controller:
    """Dispatch application requests based on HTTP verb."""

    user_facing = False

    def POST(self, group):
        """
        Schedule maintenance operations.
        """

        if group == "db":
            cherrypy.engine.publish(
                "scheduler:add",
                2,
                "maintenance:db"
            )
            cherrypy.response.status = 204
            return

        if group == "filesystem":
            cherrypy.engine.publish(
                "scheduler:add",
                2,
                "maintenance:filesystem"
            )
            return

        raise cherrypy.HTTPError(400, "Invalid task group")
