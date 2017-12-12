import cherrypy

class Controller:
    """Display request headers"""

    name = "Headers"

    exposed = True

    user_facing = True

    @cherrypy.tools.negotiable()
    def GET(self):
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
