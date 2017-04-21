import cherrypy
import apps.captures.models

class Controller:
    """Display captured requests"""

    name = "Captures"

    exposed = True

    user_facing = True

    @cherrypy.tools.negotiable()
    @cherrypy.tools.template(template="captures.html")
    def GET(self, q=None):
        manager = apps.captures.models.CaptureManager()

        if q:
            captures = manager.search(q)
        else:
            captures = manager.recent()

        return {
            "q": q,
            "captures": captures,
            "app_name": self.name
        }
