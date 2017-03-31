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

        registry = apps.registry.models.Registry()

        if u:
            parsedUrl = urlparse(u)
            bounce = registry.first(key="bounce:{}".format(parsedUrl.hostname))
            if bounce:
                destination = u.replace(parsedUrl.hostname, bounce)
                raise cherrypy.HTTPRedirect(destination)

        bounces = registry.search(key="bounce:*")

        bounce_map = {}
        for bounce in bounces:
            src = bounce["key"].replace("bounce:", "")
            dst = bounce["value"]
            bounce_map[src] = dst

        base = cherrypy.request.headers.get("Host")

        if "X-HTTPS" in cherrypy.request.headers:
            base = "https://" + base
        else:
            base = "http://" + base

        return {
            "base": base,
            "bounce_map": bounce_map,
            "app_name": self.name
        }
