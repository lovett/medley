"""Display a collection of bookmarklets."""

import cherrypy


class Controller:
    """Dispatch application requests based on HTTP verb."""

    name = "Bookmarklets"

    @staticmethod
    @cherrypy.tools.negotiable()
    def GET():
        """Present a static list of bookmarklets"""

        later_url = cherrypy.engine.publish(
            "url:internal",
            "/later"
        ).pop()

        return {
            "html": ("bookmarklets.jinja.html", {
                "later_url": later_url
            })
        }
