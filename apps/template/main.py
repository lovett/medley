"""One-line summary of the app goes here"""
import cherrypy

class Controller:
    """Dispatch application requests based on HTTP verb."""

    name = "Template"

    cache_key = "template:cache"

    @cherrypy.tools.negotiable()
    def GET(self):

        config = cherrypy.engine.publish(
            "registry:search",
            "template:*",
        ).pop()

        cached_value = cherrypy.engine.publish("cache:get", self.cache_key).pop()

        return {
            "html": ("template.html", {
                "app_name": self.name,
            }),
            "json": {"key": "value"},
            "text": "Plain text output goes here",
        }
