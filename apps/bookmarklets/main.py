"""Display a collection of bookmarklets."""

import cherrypy


class Controller:
    """Dispatch application requests based on HTTP verb."""

    name = "Bookmarklets"

    @cherrypy.tools.negotiable()
    def GET(self):
        """Present a static list of bookmarlets"""

        app_url = cherrypy.engine.publish(
            "url:for_controller", self
        ).pop()

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
            "html": ("bookmarklets.html", {
                "app_name": self.name,
                "app_url": app_url,
                "anonymizer": anonymizer,
                "ubounce": ubounce
            })
        }
