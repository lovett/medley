"""URL redirection for referrer privacy."""

import typing
import cherrypy


class Controller:
    """Dispatch application requests based on HTTP verb."""

    exposed = True
    show_on_homepage = False

    @staticmethod
    @cherrypy.tools.provides(formats=("html",))
    def GET(*_args: str, **_kwargs: str) -> bytes:
        """Perform a client-side redirect to the URL specified in the
        querystring.

        """

        return typing.cast(
            bytes,
            cherrypy.engine.publish(
                "jinja:render",
                "apps/redirect/redirect.jinja.html",
            ).pop()
        )
