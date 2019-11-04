"""
Download files from a storage bucket.
"""

import typing
import cherrypy


class Controller:
    """Dispatch application requests based on HTTP verb."""

    exposed = True
    user_facing = False

    @staticmethod
    def POST(*args: typing.Iterable[str], **_kwargs) -> None:
        """
        Dispatch to a service-specific plugin.
        """

        try:
            service = args[0]
        except IndexError:
            service = None

        if service == "gcp":
            cherrypy.engine.publish(
                "scheduler:add",
                1,
                "gcp:storage:pull",
            )
            cherrypy.response.status = 204
            return

        raise cherrypy.HTTPError(404)
