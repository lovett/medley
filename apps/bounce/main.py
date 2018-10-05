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
        "test",
    }

    @staticmethod
    def url_to_host(url):
        """Reduce a URL to its hostname"""
        parsed_url = urlparse(url)
        return parsed_url.netloc

    def host_to_group(self, host):
        """Reduce a host to a word that describes the project
        or entity it is related to.

        """

        host_without_port = host.split(":")[0]

        segments = [host_without_port]
        if "." in host_without_port:
            segments = host_without_port.split(".")

        for index, segment in enumerate(segments):
            if segment in self.common_names and index > 0:
                return segments[index - 1]

        filtered_segments = [
            segment for segment in segments
            if segment not in self.common_names
            and len(segment) > 3
        ]

        return filtered_segments[-1]

    def host_to_keyword(self, host):
        """Reduce a host to a word that distinguishes it from
        others in the same group."""

        host_without_port = host.split(":")[0]

        segments = [host_without_port]
        if "." in host_without_port:
            segments = host_without_port.split(".")

        intersect = [
            segment for segment in segments
            if segment in self.common_names
        ]

        if intersect:
            return intersect[0]

        if len(segments) > 2:
            return segments[0]

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
        return value.replace("\r", "").split("\n")

    @cherrypy.tools.negotiable()
    def GET(self, u=None, group=None):  # pylint: disable=invalid-name
        """Display all the URLs in a group."""

        host = None
        bounces = None
        name = None
        all_groups = []
        group = None

        if u:
            host = self.url_to_host(u)
            search_value = "{}\n*".format(host)
            group = cherrypy.engine.publish(
                "registry:first_key",
                value=search_value,
                key_prefix="bounce*"
            ).pop()

            if group:
                group = self.from_registry_key(group)
            else:
                group = self.host_to_group(host)
                name = self.host_to_keyword(host)

        if group:
            search_key = self.to_registry_key(group)
            bounces = cherrypy.engine.publish(
                "registry:search",
                search_key, exact=True
            ).pop()

        if bounces:
            bounces = {
                bounce["rowid"]:  self.from_registry_value(bounce["value"])
                for bounce in bounces
            }

        departing_from = None
        if host and bounces:
            # Match the current URL to a known site.
            for (_, values) in bounces.items():
                if urlparse(values[0]).netloc == host:
                    departing_from = values[1]
                    break

            # Re-scope the current URL to each known destination.
            bounces = {
                k: (u.replace(host, v[0]), v[1])
                for (k, v) in bounces.items()
            }

        if not host and not bounces:
            all_groups = cherrypy.engine.publish(
                "registry:distinct_keys", "bounce:*"
            ).pop()

        app_url = cherrypy.engine.publish("url:internal").pop()

        return {
            "html": ("bounce.jinja.html", {
                "departing_from": departing_from,
                "site": host,
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

        url_to_host = self.url_to_host(site)
        registry_key = self.to_registry_key(group)
        registry_value = self.to_registry_value(url_to_host, name)

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
