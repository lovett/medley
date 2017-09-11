import cherrypy

class Controller:
    """One-line summary of the app goes here"""

    url = "/template"

    name = "Template"

    exposed = True

    user_facing = True

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
