"""Redirection between domains"""

import typing
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

    @cherrypy.tools.provides(formats=("html",))
    def GET(self, *_args: str, **kwargs: str) -> bytes:
        """Display all the URLs in a group."""

        host = ""
        name = ""
        group = kwargs.get("group", "")
        url = kwargs.get("u", "")
        invalid = kwargs.get("invalid")
        registry_url = ""
        bounces: typing.List[typing.Tuple[str, str]] = []

        if url:
            host = self.url_to_host(url)
            key = cherrypy.engine.publish(
                "registry:first:key",
                value=host,
                key_prefix="bounce*"
            ).pop()

            try:
                _, group, name = key.split(":")
            except (AttributeError, ValueError):
                group = self.host_to_group(host)
                name = self.host_to_keyword(host)

        if group:
            _, rows = cherrypy.engine.publish(
                "registry:search",
                f"bounce:{group}"
            ).pop()

            if rows:
                bounces = [
                    (url.replace(host, row["value"]),
                     row["key"].split(":").pop())
                    for row in rows
                ]

            registry_url = cherrypy.engine.publish(
                "url:internal",
                "/registry",
                {"q": f"bounce:{group}"}
            ).pop()

        if not any(host in bounce[0] for bounce in bounces):
            bounces = []

        response: bytes = cherrypy.engine.publish(
            "jinja:render",
            "apps/bounce/bounce.jinja.html",
            url=url,
            site=host,
            group=group,
            name=name,
            bounces=bounces,
            registry_url=registry_url,
            invalid=invalid
        ).pop()

        return response

    def POST(self, url: str, name: str, group: str) -> None:
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

        cherrypy.engine.publish(
            "registry:replace",
            f"bounce:{group}:{name}",
            host
        )

        redirect_url = cherrypy.engine.publish(
            "url:internal",
            None,
            {"group": group}
        ).pop()

        raise cherrypy.HTTPRedirect(redirect_url)

    def host_to_group(self, host: str = "") -> str:
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

    def host_to_keyword(self, host: str = "") -> str:
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
    def url_to_host(url: str = "") -> str:
        """Reduce a URL to its hostname"""
        parsed_url = urlparse(url)
        if not parsed_url.netloc:
            return url
        return parsed_url.netloc
