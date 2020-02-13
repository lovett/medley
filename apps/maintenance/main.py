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

        topic = ""
        if group == "db":
            topic = "maintenance:db"

        if not topic:
            raise cherrypy.HTTPError(400, "Invalid task group")

        cherrypy.engine.publish(
            "scheduler:add",
            2,
            topic
        )

        cherrypy.response.status = 204
