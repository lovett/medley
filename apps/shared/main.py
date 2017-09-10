import cherrypy

class Controller:
    """Serve static assets used by multiple apps"""

    url = "/shared"

    name = "Shared"

    exposed = True

    user_facing = False

    def GET(self):
        raise cherrypy.HTTPRedirect("/")
