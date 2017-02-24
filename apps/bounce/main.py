import cherrypy
import tools.negotiable
import tools.jinja
import apps.registry.models
from urllib.parse import urlparse, urlunparse

class Controller:
    """Redirect to an equivalent page on a different domain."""

    name = "Bounce"

    exposed = True

    user_facing = True

    @cherrypy.tools.template(template="bounce.html")
    @cherrypy.tools.negotiable()
    def GET(self, u=None):

        if u:
            parsedUrl = urlparse(u)
            key = "bounce:{}".format(parsedUrl.hostname)
        else:
            parsedUrl = None
            key = "bounce:*"

        registry = apps.registry.models.Registry()
        bounces = registry.search(key=key)

        bounce_map = {}
        for bounce in bounces:
            src = bounce["key"].replace("bounce:", "")
            dst = bounce["value"]
            bounce_map[src] = dst

        return {
            "bounce_map": bounce_map,
            "app_name": self.name
        }
