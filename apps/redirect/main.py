import cherrypy
import urllib.parse

class Controller:
    """URL redirection without referrer"""

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
