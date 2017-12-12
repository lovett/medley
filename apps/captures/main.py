import cherrypy

class Controller:
    """Display captured requests"""

    name = "Captures"

    exposed = True

    user_facing = True

    @cherrypy.tools.negotiable()
    def GET(self, q=None):
        if q:
            captures = cherrypy.engine.publish("capture:search", q).pop()
        else:
            captures = cherrypy.engine.publish("capture:recent").pop()

        return {
            "html": ("captures.html", {
                "q": q,
                "captures": captures,
                "app_name": self.name
            })
        }
