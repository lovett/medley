import cherrypy

class Controller:
    """A collection of bookmarklets"""

    name = "Bookmarklets"

    exposed = True

    user_facing = True

    @cherrypy.tools.negotiable()
    def GET(self):

        return {
            "html": ("bookmarklets.html", {
                "app_name": self.name,
            })
        }
