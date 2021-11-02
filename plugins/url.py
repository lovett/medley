"""Work out an app URL from a controller instance."""

import ipaddress
import typing
from urllib.parse import urlencode, urlparse
import cherrypy


class Plugin(cherrypy.process.plugins.SimplePlugin):
    """A CherryPy plugin for building app-specific URLs."""

    def __init__(self, bus: cherrypy.process.wspbus.Bus) -> None:
        cherrypy.process.plugins.SimplePlugin.__init__(self, bus)

    def start(self) -> None:
        """Define the CherryPy messages to listen for.

        This plugin owns the url prefix.
        """
        self.bus.subscribe("url:internal", self.internal_url)

    @staticmethod
    def internal_url(
            path: typing.Optional[str] = None,
            query: typing.Optional[typing.Dict[str, typing.Any]] = None,
    ) -> str:
        """Create an absolute internal URL.

        The URL hostname is sourced from two places. Most of the time,
        there will be an incoming request at hand and
        cherrypy.request.base will hold the desired value.

        If there isn't an incoming request, fall back to a value
        stored in the registry. If that's not available, fall back to
        a domain-relative URL.

        """

        hostname = ''
        scheme = ''

        parsed_url = urlparse(
            cherrypy.request.base
        )

        if parsed_url.netloc:
            hostname = parsed_url.netloc

        if parsed_url.scheme:
            scheme = parsed_url.scheme

        try:
            if ipaddress.ip_address(hostname).is_loopback:
                hostname = ''
                scheme = ''
        except ValueError:
            pass

        if not hostname:
            config_url = cherrypy.engine.publish(
                "registry:first:value",
                "config:base_url"
            ).pop()

            parsed_url = urlparse(
                config_url
            )

            hostname = parsed_url.netloc
            scheme = parsed_url.scheme

        if scheme:
            scheme = f"{scheme}://"

        # A non-root path is treated as a sub-path of the current app.
        if path and not path.startswith("/"):
            path = f"{cherrypy.request.script_name}/{path}"

        url = f"{scheme}{hostname}{path or cherrypy.request.script_name}/"

        if query:
            query = {
                key: value
                for (key, value) in query.items()
                if value
            }
            url = f"{url}?{urlencode(query)}"

        request_headers = cherrypy.request.headers
        use_https = request_headers.get("X-Https", "") == "On"

        if not use_https:
            use_https = request_headers.get("X-Forwarded-Proto", "") == "https"

        if use_https:
            url = f"https:{url.split(':', 1).pop()}"

        return url
