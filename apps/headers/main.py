"""
Display request headers
"""

import cherrypy


class Controller:
    """
    The primary controller for the application, structured for
    method-based dispatch
    """

    name = "Headers"

    exposed = True

    user_facing = True

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
            "html": ("headers.html", {
                "headers": headers,
                "app_name": self.name,
            })
        }
