import cherrypy
import urllib.parse

class Controller:
    """URL redirection without referrer"""

    name = "Redirect"

    exposed = True

    user_facing = True

    @cherrypy.tools.negotiable()
    def GET(self, **kwargs):
        dest = cherrypy.request.query_string
        if "u" in kwargs:
            dest = kwargs["u"]

        if "%3A" in dest:
            dest = urllib.parse.unquote_plus(dest)

        return {
            "html": ("redirect.html", {
                "app_name": self.name,
                "dest": dest
            })
        }
