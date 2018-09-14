"""Redirect to an equivalent page on a different domain."""

from urllib.parse import urlparse
import cherrypy


class Controller:
    """Dispatch application requests based on HTTP verb."""

    name = "Bounce"

    common_names = {
        "dev",
        "stage",
        "staging",
        "local",
    }

    @staticmethod
    def site_url(url):
        """Reduce a URL to its root: protocol and domain"""
        parsed_url = urlparse(url)
        return "{}://{}".format(parsed_url.scheme, parsed_url.netloc)

    def guess_group(self, url):
        """Reduce a URL to its domain with no suffixes or prefixes"""

        parsed_url = urlparse(url)

        segments = parsed_url.hostname.split(".")

        if len(segments) > 1:
            segments.pop()

        diff = [
            segment for segment in segments
            if segment not in self.common_names
            and len(segment) > 2
        ]

        return diff[-1]

    def guess_name(self, url):
        """Reduce a URL to a keyword"""

        parsed_url = urlparse(url)

        segments = parsed_url.hostname.split(".")

        intersect = [
            segment for segment in segments
            if segment in self.common_names
        ]

        if intersect:
            return intersect[0]

        if len(segments) == 1:
            return "dev"

        return "live"

    @staticmethod
    def to_registry_key(value):
        """Convert a value to a registry key using the application
        namespace.

        """
        return "bounce:{}".format(value)

    @staticmethod
    def from_registry_key(value):
        """Remove the application namespace from a registry key."""
        return value.replace("bounce:", "")

    @staticmethod
    def to_registry_value(url, name):
        """Join a URL and name into a value that can be stored in the
        registry.

        """
        return "{}\n{}".format(url, name)

    @staticmethod
    def from_registry_value(value):
        """Extract a URL and name from a registry value."""
        return value.split("\n")

    @cherrypy.tools.negotiable()
    def GET(self, u=None, group=None):  # pylint: disable=invalid-name
        """Display all the URLs in a group."""

        site = False
        bounces = None
        name = None
        all_groups = []
        group = None

        if u:
            site = self.site_url(u)
            search_value = "{}\n*".format(site)
            group = cherrypy.engine.publish(
                "registry:first_key",
                value=search_value,
                key_prefix="bounce*"
            ).pop()

            if group:
                group = self.from_registry_key(group)

        if group:
            search_key = self.to_registry_key(group)
            bounces = cherrypy.engine.publish(
                "registry:search",
                search_key, exact=True
            ).pop()

        if site and not group:
            group = self.guess_group(site)
            name = self.guess_name(site)

        if bounces:
            bounces = {
                bounce["rowid"]:  self.from_registry_value(bounce["value"])
                for bounce in bounces
            }

        departing_from = None
        if site and bounces:
            # Match the current URL to a known site.
            for (_, values) in bounces.items():
                if urlparse(site).netloc == urlparse(values[0]).netloc:
                    departing_from = values[1]
                    break

            # Re-scope the current URL to each known destination.
            bounces = {
                k: (u.replace(site, v[0]), v[1])
                for (k, v) in bounces.items()
            }

        if not site and not bounces:
            all_groups = cherrypy.engine.publish(
                "registry:distinct_keys", "bounce:*"
            ).pop()

        app_url = cherrypy.engine.publish("url:internal").pop()

        return {
            "html": ("bounce.jinja.html", {
                "departing_from": departing_from,
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
        """Add a new URL to a group."""

        site_url = self.site_url(site)
        registry_key = self.to_registry_key(group)
        registry_value = self.to_registry_value(site_url, name)

        cherrypy.engine.publish(
            "registry:add",
            registry_key,
            [registry_value],
            replace=False
        )

        cherrypy.response.status = 204

    @staticmethod
    def DELETE(uid):
        """Remove a site from a group by its ID."""
        cherrypy.engine.publish("registry:remove_id", uid)
        cherrypy.response.status = 204
