import cherrypy

class Controller:
    """Serve static assets used by multiple apps"""

    URL = "/shared"

    exposed = True

    user_facing = False

    def GET(self):
        raise cherrypy.HTTPRedirect("/")
