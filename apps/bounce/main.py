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
        else:
            parsedUrl = None

        registry = apps.registry.models.Registry()
        key = "bounce:{}".format(parsedUrl.hostname)
        bounces = registry.search(key=key)

        bounces = [u.replace(parsedUrl.hostname, bounce["value"]) for bounce in bounces]

        print(bounces)

        return {
            "hostname": parsedUrl.hostname,
            "app_name": self.name
        }
