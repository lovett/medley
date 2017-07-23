import cherrypy
import apps.registry.models
from urllib.parse import urlparse, urlunparse

class Controller:
    """Redirect to an equivalent page on a different domain."""

    name = "Bounce"

    exposed = True

    user_facing = True

    common_names = {
        "dev",
        "stage",
        "staging",
    }

    def siteUrl(self, url):
        parsedUrl = urlparse(url)
        return "{}://{}".format(parsedUrl.scheme, parsedUrl.netloc)

    def guessGroup(self, url):
        parsedUrl = urlparse(url)
        host_segments = set(parsedUrl.hostname.split(".")[0:-1])
        diff = host_segments.difference(self.common_names)

        return next(iter(diff))

    def guessName(self, url):
        parsedUrl = urlparse(url)
        host_segments = set(parsedUrl.hostname.split("."))

        intersect = self.common_names.intersection(host_segments)

        if len(intersect):
            return next(iter(intersect))
        else:
            return "live"

    def toRegistryKey(self, value):
        return "bounce:{}".format(value)

    def fromRegistryKey(self, value):
        return value.replace("bounce:", "")

    def toRegistryValue(self, url, name):
        return "{}\n{}".format(url, name)

    def fromRegistryValue(self, value):
        return value.split("\n")


    @cherrypy.tools.template(template="bounce.html")
    @cherrypy.tools.negotiable()
    def GET(self, u=None, group=None):
        site = False
        bounces = None
        name = None
        all_groups = []

        registry = apps.registry.models.Registry()

        if u:
            site = self.siteUrl(u)
            search_value = "{}*".format(site)
            group = registry.firstKey(value=search_value)
            if group:
                group = self.fromRegistryKey(group)

        if group:
            search_key = self.toRegistryKey(group)
            bounces = registry.search(search_key, exact=True)

        if site and not group:
            group = self.guessGroup(site)
            name = self.guessName(site)

        if bounces:
            bounces = {bounce["rowid"]:  self.fromRegistryValue(bounce["value"]) for bounce in bounces}

        if site and bounces:
            bounces = {
                k: (u.replace(site, v[0]), v[1])
                for (k, v) in bounces.items()
                if site not in v[0]
            }


        if not site and not bounces:
            all_groups = registry.distinctKeys("bounce:*")

        app_url = cherrypy.request.headers.get("Host")

        if "X-HTTPS" in cherrypy.request.headers:
            app_url = "https://" + app_url
        else:
            app_url = "http://" + app_url

        return {
            "site": site,
            "group": group,
            "all_groups": all_groups,
            "name": name,
            "app_url": app_url,
            "bounces": bounces,
            "app_name": self.name
        }

    @cherrypy.tools.negotiable()
    def PUT(self, site, name, group):
        registry = apps.registry.models.Registry()

        site_url = self.siteUrl(site)
        registry_key = self.toRegistryKey(group)
        registry_value = self.toRegistryValue(site_url, name)

        uid = registry.add(
            registry_key,
            registry_value,
            replace=False
        )

        if cherrypy.request.headers.get("X-Requested-With", None) == "XMLHttpRequest":
            return {"uid": uid, "group": group }
        else:
            raise cherrypy.HTTPRedirect("/bounce?group={}".format(group))

    def DELETE(self, uid):
        registry = apps.registry.models.Registry()
        records = registry.find(uid)

        if len(records) == 0:
            raise cherrypy.HTTPError(404, "Invalid id")

        record = records[0]

        removals = registry.remove(uid=uid)

        if removals != 1:
            cherrypy.HTTPError(400)
