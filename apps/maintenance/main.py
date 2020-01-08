"""Perform maintenance tasks."""

import cherrypy


class Controller:
    """Dispatch application requests based on HTTP verb."""

    show_on_homepage = False
    exposed = True

    @staticmethod
    def POST(*_args, **kwargs) -> None:
        """
        Schedule maintenance operations.
        """

        group = kwargs.get("group")

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

            cherrypy.response.status = 204
            return

        raise cherrypy.HTTPError(400, "Invalid task group")
