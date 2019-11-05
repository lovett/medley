"""
Download files from a storage bucket.
"""

import cherrypy


class Controller:
    """Dispatch application requests based on HTTP verb."""

    exposed = True
    user_facing = False

    @staticmethod
    def POST(*_args, **kwargs) -> None:
        """
        Dispatch to a service-specific plugin.
        """

        service = kwargs.get("service")

        if service == "gcp":
            cherrypy.engine.publish(
                "scheduler:add",
                1,
                "gcp:storage:pull",
            )
            cherrypy.response.status = 204
            return

        raise cherrypy.HTTPError(404)
