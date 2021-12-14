"""Perform maintenance tasks."""

import cherrypy


class Controller:
    """Dispatch application requests based on HTTP verb."""

    show_on_homepage = False
    exposed = True

    @staticmethod
    def POST() -> None:
        """Schedule maintenance operations."""

        cherrypy.engine.publish(
            "scheduler:add",
            2,
            "maintenance"
        )

        cherrypy.response.status = 204

    @staticmethod
    def DELETE(*args: str, **_kwargs: str) -> None:
        """Perform deletion-oriented on-demand maintenance tasks."""

        if "memorize" in args:
            cherrypy.engine.publish(
                "memorize:clear"
            )
            cherrypy.response.status = 204
            return

        raise cherrypy.NotFound()
