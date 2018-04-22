"""Display previously-captured requests."""

import cherrypy


class Controller:
    """Dispatch application requests based on HTTP verb."""

    name = "Captures"

    @cherrypy.tools.negotiable()
    def GET(self, query=None):
        """Display a list of recent captures, or captures matching a search
        query.

        """

        if query:
            captures = cherrypy.engine.publish("capture:search", query).pop()
        else:
            captures = cherrypy.engine.publish("capture:recent").pop()

        return {
            "html": ("captures.html", {
                "query": query,
                "captures": captures,
                "app_name": self.name
            })
        }
