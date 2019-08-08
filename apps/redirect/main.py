"""URL redirection for referrer privacy."""

import cherrypy


class Controller:
    """Dispatch application requests based on HTTP verb."""

    name = "Redirect"

    user_facing = False

    @staticmethod
    @cherrypy.tools.negotiable()
    def GET(*_args, **_kwargs):
        """Perform a client-side redirect to the URL specified in the
        querystring.

        """
        return {
            "html": ("redirect.jinja.html", None)
        }
