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

    def siteUrl(self, url):
        parsedUrl = urlparse(url)
        return "{}://{}".format(parsedUrl.scheme, parsedUrl.netloc)

    def toRegistryKey(self, value):
        return "bounce:{}".format(value)

    def fromRegistryKey(self, value):
        return value.replace("bounce:", "")


    @cherrypy.tools.template(template="bounce.html")
    @cherrypy.tools.negotiable()
    def GET(self, u=None):
        site = False
        group = False
        bounces = None

        registry = apps.registry.models.Registry()

        if u:
            site = self.siteUrl(u)
            group = registry.firstKey(value=site)

        if group:
            group = self.fromRegistryKey(group)
            bounces = registry.search(key=group)

        if site and bounces:
            bounces = {bounce["rowid"]:  u.replace(site, bounce["value"]) for bounce in bounces}

        app_url = cherrypy.request.headers.get("Host")

        if "X-HTTPS" in cherrypy.request.headers:
            app_url = "https://" + app_url
        else:
            app_url = "http://" + app_url


        return {
            "site": site,
            "group": group,
            "app_url": app_url,
            "bounces": bounces,
            "app_name": self.name
        }

    @cherrypy.tools.negotiable()
    def PUT(self, site, group):
        registry = apps.registry.models.Registry()

        key = self.toRegistryKey(group)

        uid = registry.add(
            key,
            self.siteUrl(site),
            replace=False
        )

        if cherrypy.request.headers.get("X-Requested-With", None) == "XMLHttpRequest":
            return {"uid": uid }
        else:
            raise cherrypy.HTTPRedirect("/bounce")

    def DELETE(self, uid):
        registry = apps.registry.models.Registry()
        records = registry.find(uid)

        if len(records) == 0:
            raise cherrypy.HTTPError(404, "Invalid id")

        record = records[0]

        removals = registry.remove(uid=uid)

        if removals != 1:
            cherrypy.HTTPError(400)
