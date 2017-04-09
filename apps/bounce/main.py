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
        bounceless_domain = False

        bounce_map = {}

        registry = apps.registry.models.Registry()

        if u:
            parsedUrl = urlparse(u)
            bounce = registry.first(key="bounce:{}".format(parsedUrl.netloc))
            if not bounce:
                bounceless_domain = parsedUrl.netloc
            else:
                destination = u.replace(parsedUrl.netloc, bounce)
                raise cherrypy.HTTPRedirect(destination)

        bounces = registry.search(key="bounce:*")


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
            "bounceless_domain": bounceless_domain,
            "base": base,
            "bounce_map": bounce_map,
            "app_name": self.name
        }

    @cherrypy.tools.negotiable()
    def PUT(self, source, destination):
        registry = apps.registry.models.Registry()

        if source.startswith("http"):
            parsedSource = urlparse(source)
            source = parsedSource.netloc

        if destination.startswith("http"):
            parsedDestination = urlparse(destination)
            destination = parsedDestination.netloc

        uid = registry.add(
            "bounce:{}".format(source),
            destination,
            replace=False
        )

        if cherrypy.request.headers.get("X-Requested-With", None) == "XMLHttpRequest":
            return {"uid": uid }
        else:
            raise cherrypy.HTTPRedirect("/bounce")
