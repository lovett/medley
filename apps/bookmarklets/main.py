"""Display a collection of bookmarklets."""

import cherrypy


class Controller:
    """Dispatch application requests based on HTTP verb."""

    name = "Bookmarklets"

    @cherrypy.tools.negotiable()
    @staticmethod
    def GET():
        """Present a static list of bookmarklets"""

        anonymizer = cherrypy.engine.publish(
            "registry:first_value",
            "config:url_anonymizer",
            memorize=True
        ).pop()

        ubounce = cherrypy.engine.publish(
            "registry:first_value",
            "bookmarklets:ubounce",
        ).pop()

        return {
            "html": ("bookmarklets.jinja.html", {
                "anonymizer": anonymizer,
                "ubounce": ubounce
            })
        }
