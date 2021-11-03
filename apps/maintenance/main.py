"""Perform maintenance tasks."""

import cherrypy


class Controller:
    """Dispatch application requests based on HTTP verb."""

    show_on_homepage = False
    exposed = True

    @staticmethod
    def POST(*_args: str, **_kwargs: str) -> None:
        """Schedule maintenance operations."""

        cherrypy.engine.publish(
            "scheduler:add",
            2,
            "maintenance"
        )

        cherrypy.response.status = 204
