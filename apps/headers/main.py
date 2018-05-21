"""Display request headers."""

import cherrypy


class Controller:
    """Dispatch application requests based on HTTP verb."""

    name = "Headers"

    @cherrypy.tools.negotiable()
    def GET(self):
        """Display the headers of the current request"""
        headers = sorted(
            cherrypy.request.headers.items(),
            key=lambda pair: pair[0]
        )

        return {
            "json": headers,
            "text": ["{}: {}".format(*header) for header in headers],
            "html": ("headers.jinja.html", {
                "headers": headers,
                "app_name": self.name,
            })
        }
