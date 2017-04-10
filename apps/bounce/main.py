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

    def baseUrl(self, url):
        parsedUrl = urlparse(url)
        return "{}://{}".format(parsedUrl.scheme, parsedUrl.netloc)

    def toRegistryKey(self, value):
        return "bounce:{}".format(value)

    def fromRegistryKey(self, value):
        return value.replace("bounce:", "")


    @cherrypy.tools.template(template="bounce.html")
    @cherrypy.tools.negotiable()
    def GET(self, u=None):
        source = False

        bounce_map = {}

        registry = apps.registry.models.Registry()

        if u:
            source = self.baseUrl(u)
            key = self.toRegistryKey(source)
            bounce = registry.first(key=key)
            if bounce:
                destination = u.replace(self.baseUrl(u), bounce)
                raise cherrypy.HTTPRedirect(destination)

        bounces = registry.search(key="bounce:*")

        for bounce in bounces:
            src = self.fromRegistryKey(bounce["key"])
            dst = bounce["value"]
            bounce_map[src] = dst

        app_url = cherrypy.request.headers.get("Host")

        if "X-HTTPS" in cherrypy.request.headers:
            app_url = "https://" + app_url
        else:
            app_url = "http://" + app_url

        return {
            "source": source,
            "app_url": app_url,
            "bounce_map": bounce_map,
            "app_name": self.name
        }

    @cherrypy.tools.negotiable()
    def PUT(self, source, destination):
        registry = apps.registry.models.Registry()

        source = self.baseUrl(source)

        key = self.toRegistryKey(source)
        uid = registry.add(
            key,
            destination,
            replace=False
        )

        if cherrypy.request.headers.get("X-Requested-With", None) == "XMLHttpRequest":
            return {"uid": uid }
        else:
            raise cherrypy.HTTPRedirect("/bounce")
