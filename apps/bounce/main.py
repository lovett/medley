"""Redirect to an equivalent page on a different domain."""

from urllib.parse import urlparse
import cherrypy


class Controller:
    """Dispatch application requests based on HTTP verb."""

    exposed = True
    show_on_homepage = True

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

    @cherrypy.tools.provides(formats=("html",))
    def GET(self, *_args, **kwargs) -> bytes:
        """Display all the URLs in a group."""

        host = ''
        bounces = ''
        name = ''
        group = kwargs.get('group', '')
        url = kwargs.get('u', '')
        invalid = kwargs.get('invalid')
        registry_url = ''

        if url:
            host = self.url_to_host(url)
            record = cherrypy.engine.publish(
                "registry:first:key",
                value=host,
                key_prefix="bounce*"
            ).pop()

            try:
                _, group, name = record.split(":")
            except (AttributeError, ValueError):
                group = self.host_to_group(host)
                name = self.host_to_keyword(host)

        if group:
            search_key = f"bounce:{group}:"
            bounces = cherrypy.engine.publish(
                "registry:search",
                search_key
            ).pop()

            registry_url = cherrypy.engine.publish(
                "url:internal",
                "/registry",
                {"q": f"bounce:{group}"}
            ).pop()

        departing_from = None
        if bounces:
            # Match the current URL to a known site.
            for bounce in bounces:
                if bounce["value"] == host:
                    departing_from = bounce["key"].split(":").pop()
                    break

            # If the departing site can't be determined, the
            # list of bounces isn't viable.
            if not departing_from:
                bounces = []

            # Re-scope the current URL to each known destination.
            bounces = [
                (url.replace(host, bounce["value"]),
                 bounce["key"].split(":").pop())
                for bounce in bounces
            ]

        return cherrypy.engine.publish(
            "jinja:render",
            "bounce.jinja.html",
            departing_from=departing_from,
            url=url,
            site=host,
            group=group,
            name=name,
            bounces=bounces,
            registry_url=registry_url,
            invalid=invalid
        ).pop()

    def POST(self, url, name, group) -> None:
        """Add a new URL to a group."""

        host = self.url_to_host(url)

        group = cherrypy.engine.publish(
            "formatting:string_sanitize",
            group
        ).pop()

        if not group:
            redirect_url = cherrypy.engine.publish(
                "url:internal",
                None,
                {"name": name, "url": url, "invalid": "group"}
            ).pop()

            raise cherrypy.HTTPRedirect(redirect_url)

        name = cherrypy.engine.publish(
            "formatting:string_sanitize",
            name
        ).pop()

        if not name:
            redirect_url = cherrypy.engine.publish(
                "url:internal",
                None,
                {"url": url, "group": group, "invalid": "name"}
            ).pop()

            raise cherrypy.HTTPRedirect(redirect_url)

        key = f"bounce:{group}:{name}"

        cherrypy.engine.publish(
            "registry:add",
            key,
            [host],
            replace=True
        )

        redirect_url = cherrypy.engine.publish(
            "url:internal",
            None,
            {"group": group}
        ).pop()

        raise cherrypy.HTTPRedirect(redirect_url)
