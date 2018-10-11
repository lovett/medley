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
    def url_to_host(url=None):
        """Reduce a URL to its hostname"""
        parsed_url = urlparse(url)
        if not parsed_url.netloc:
            return url
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

    @cherrypy.tools.negotiable()
    def GET(self, u=None, group=None):  # pylint: disable=invalid-name
        """Display all the URLs in a group."""

        host = None
        bounces = None
        name = None
        group = None

        if u:
            host = self.url_to_host(u)
            record = cherrypy.engine.publish(
                "registry:first_key",
                value=host,
                key_prefix="bounce*"
            ).pop()

            try:
                _, group, name = record.split(":")
            except (AttributeError, ValueError):
                group = self.host_to_group(host)
                name = self.host_to_keyword(host)

        if group:
            search_key = "bounce:{}".format(group)
            bounces = cherrypy.engine.publish(
                "registry:search",
                search_key,
            ).pop()

        departing_from = None
        if host and bounces:
            # Match the current URL to a known site.
            for bounce in bounces:
                if bounce["value"] == host:
                    departing_from = bounce["key"].split(":").pop()
                    break

            # Re-scope the current URL to each known destination.
            bounces = {
                bounce["rowid"]: (
                    u.replace(host, bounce["value"]),
                    bounce["key"].split(":").pop()
                )
                for bounce in bounces
            }

        app_url = cherrypy.engine.publish("url:internal").pop()

        return {
            "html": ("bounce.jinja.html", {
                "departing_from": departing_from,
                "site": host,
                "group": group,
                "name": name,
                "app_url": app_url,
                "bounces": bounces,
                "app_name": self.name
            })
        }

    def PUT(self, site, name, group):
        """Add a new URL to a group."""

        host = self.url_to_host(site)

        key = "bounce:{}:{}".format(group, name)

        cherrypy.engine.publish(
            "registry:add",
            key,
            [host],
            replace=True
        )

        cherrypy.response.status = 204

    @staticmethod
    def DELETE(uid):
        """Remove a site from a group by its ID."""
        cherrypy.engine.publish("registry:remove_id", uid)
        cherrypy.response.status = 204
