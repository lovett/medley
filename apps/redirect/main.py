"""URL redirection for referrer privacy."""

from urllib.parse import unquote_plus
import cherrypy


class Controller:
    """Dispatch application requests based on HTTP verb."""

    name = "Redirect"

    @cherrypy.tools.negotiable()
    def GET(self, u=None):  # pylint: disable=invalid-name
        """Perform a client-side redirect to the URL specified in the
        querystring.

        """

        if u is not None:
            u = unquote_plus(u)

        return {
            "html": ("redirect.jinja.html", {
                "app_name": self.name,
                "dest": u
            })
        }
