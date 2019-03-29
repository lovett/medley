"""Display a collection of bookmarklets."""

import cherrypy


class Controller:
    """Dispatch application requests based on HTTP verb."""

    name = "Bookmarklets"

    @staticmethod
    @cherrypy.tools.negotiable()
    def GET():
        """Present a static list of bookmarklets"""

        anonymizer = cherrypy.engine.publish(
            "url:internal",
            "/redirect/?u="
        ).pop()

        return {
            "html": ("bookmarklets.jinja.html", {
                "anonymizer": anonymizer,
            })
        }
