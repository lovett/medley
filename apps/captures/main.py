"""Display previously-captured requests."""

import cherrypy


class Controller:
    """Dispatch application requests based on HTTP verb."""

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
