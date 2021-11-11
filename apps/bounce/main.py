"""Redirection between domains"""

import typing
import cherrypy
from pydantic import BaseModel
from pydantic import ValidationError
from pydantic import Field
from pydantic import HttpUrl
from resources.url import Url


class GetParams(BaseModel):
    """Valid request parameters for GET requests."""
    u: HttpUrl = Field("")
    group: str = ""
    error: str = ""
    site_name: str = ""


class PostParams(BaseModel):
    """Valid request parameters for POST requests."""
    url: str = ""
    name: str = ""
    group: str = Field(
        "",
        strip_whitespace=True,
        to_lower=True,
        min_length=1
    )


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
    def GET(self, **kwargs: str) -> bytes:
        """Display all the URLs in a group."""

        try:
            params = GetParams(**kwargs)
        except ValidationError as error:
            raise cherrypy.HTTPError(400) from error

        registry_url = ""
        bounces: typing.List[Url] = []

        url = Url(params.u)

        if params.u:
            registry_key = cherrypy.engine.publish(
                "registry:first:key",
                value=url.base_address,
                key_prefix="bounce*"
            ).pop()

            try:
                _, params.group, params.site_name = registry_key.split(":")
            except (AttributeError, ValueError):
                params.group = self.url_to_group(url.base_address)
                params.site_name = self.url_to_name(url.base_address)

        if params.group:
            _, rows = cherrypy.engine.publish(
                "registry:search",
                f"bounce:{params.group}"
            ).pop()

            if rows:
                bounces = [
                    Url(
                        url.address.replace(
                            url.base_address,
                            row["value"]
                        ),
                        row["key"].split(":").pop()
                    )
                    for row in rows
                ]

            registry_url = cherrypy.engine.publish(
                "app_url",
                "/registry",
                {"q": f"bounce:{params.group}"}
            ).pop()

        if url not in bounces:
            bounces = []

        return cherrypy.engine.publish(
            "jinja:render",
            "apps/bounce/bounce.jinja.html",
            url=url,
            site=url.base_address,
            group=params.group,
            name=params.site_name,
            bounces=bounces,
            registry_url=registry_url,
            error=params.error
        ).pop()

    @staticmethod
    def POST(url: str, name: str, group: str) -> None:
        """Add a new URL to a group."""

        try:
            params = PostParams(url=url, name=name, group=group)
        except ValidationError as error:
            raise cherrypy.HTTPError(400) from error

        host = Url(params.url).base_address

        cherrypy.engine.publish(
            "registry:replace",
            f"bounce:{params.group}:{params.name}",
            host
        )

        redirect_url = cherrypy.engine.publish(
            "app_url",
            "",
            {"group": params.group}
        ).pop()

        raise cherrypy.HTTPRedirect(redirect_url)

    def url_to_group(self, host: str = "") -> str:
        """Reduce a URL to a word that describes the project
        or entity it is related to."""

        host_without_scheme = host.split("://")[-1]
        host_without_port = host_without_scheme.split(":")[0]

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

    def url_to_name(self, host: str = "") -> str:
        """Reduce a URL to a word that distinguishes it from
        others in the same group."""

        url_without_scheme = host.split("://")[-1]
        url_without_port = url_without_scheme.split(":")[0]

        segments = [url_without_port]
        if "." in url_without_port:
            segments = url_without_port.split(".")

        intersect = [
            segment for segment in segments
            if segment in self.common_names
        ]

        if intersect:
            return intersect[0]

        if len(segments) > 2:
            return segments[0]

        return "live"
