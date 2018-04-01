"""URL redirection for referrer privacy."""

import cherrypy
import urllib.parse


class Controller:
    """Dispatch application requests based on HTTP verb."""

    name = "Redirect"

    exposed = True

    user_facing = True

    @cherrypy.tools.negotiable()
    def GET(self, u=None):

        if u is not None:
            u = urllib.parse.unquote_plus(u)

        return {
            "html": ("redirect.html", {
                "app_name": self.name,
                "dest": u
            })
        }
