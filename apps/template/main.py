"""One-line summary of the app goes here"""

import cherrypy


class Controller:
    """Dispatch application requests based on HTTP verb."""

    name = "Template"

    @cherrypy.tools.negotiable()
    def GET(self):
        """Lorem ipsum dolor sit"""

        return {
            "html": ("template.html", {
                "app_name": self.name,
            }),
            "json": {"key": "value"},
            "text": "Plain text output goes here",
        }
