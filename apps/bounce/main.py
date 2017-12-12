import cherrypy
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
        "local",
    }

    def siteUrl(self, url):
        """Reduce a URL to its root: protocol and domain"""
        parsedUrl = urlparse(url)
        return "{}://{}".format(parsedUrl.scheme, parsedUrl.netloc)

    def guessGroup(self, url):
        """Reduce a URL to its domain with no suffixes or prefixes"""

        parsedUrl = urlparse(url)

        segments = parsedUrl.hostname.split(".")

        if len(segments) > 1:
            segments.pop()

        diff = [
            segment for segment in segments
            if segment not in self.common_names
            and len(segment) > 2
        ]
        return diff[-1]

    def guessName(self, url):
        """Reduce a URL to a keyword"""

        parsedUrl = urlparse(url)

        segments = parsedUrl.hostname.split(".")

        intersect = [
            segment for segment in segments
            if segment in self.common_names
        ]

        if len(intersect):
            return intersect[0]

        if len(segments) == 1:
            return "dev"

        return "live"


    def toRegistryKey(self, value):
        return "bounce:{}".format(value)

    def fromRegistryKey(self, value):
        return value.replace("bounce:", "")

    def toRegistryValue(self, url, name):
        return "{}\n{}".format(url, name)

    def fromRegistryValue(self, value):
        return value.split("\n")

    @cherrypy.tools.negotiable()
    def GET(self, u=None, group=None):
        site = False
        bounces = None
        name = None
        all_groups = []
        group = None

        if u:
            site = self.siteUrl(u)
            search_value = "{}*".format(site)
            group = cherrypy.engine.publish("registry:first_key", search_value).pop()
            if group:
                group = self.fromRegistryKey(group)

        if group:
            search_key = self.toRegistryKey(group)
            bounces = cherrypy.engine.publish("registry:search", search_key, exact=True).pop()

        if site and not group:
            group = self.guessGroup(site)
            name = self.guessName(site)

        if bounces:
            bounces = {
                bounce["rowid"]:  self.fromRegistryValue(bounce["value"])
                for bounce in bounces
            }

        if site and bounces:
            bounces = {
                k: (u.replace(site, v[0]), v[1])
                for (k, v) in bounces.items()
                if site not in v[0]
            }

        if not site and not bounces:
            all_groups = cherrypy.engine.publish(
                "registry:distinct_keys", "bounce:*"
            ).pop()

        app_url = cherrypy.request.headers.get("Host")

        if "X-HTTPS" in cherrypy.request.headers:
            app_url = "https://" + app_url
        else:
            app_url = "http://" + app_url

        return {
            "html": ("bounce.html", {
                "site": site,
                "group": group,
                "all_groups": all_groups,
                "name": name,
                "app_url": app_url,
                "bounces": bounces,
                "app_name": self.name
            })
        }

    def PUT(self, site, name, group):
        site_url = self.siteUrl(site)
        registry_key = self.toRegistryKey(group)
        registry_value = self.toRegistryValue(site_url, name)

        cherrypy.engine.publish(
            "registry:add",
            registry_key,
            [registry_value],
            replace=False
        )

        cherrypy.response.status = 204
