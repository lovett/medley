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
        self.bus.subscribe("url:current", self.current_url)
        self.bus.subscribe("url:internal", self.internal_url)
        self.bus.subscribe("url:alt", self.alt_url)
        self.bus.subscribe("url:readable", self.readable_url)
        self.bus.subscribe(
            "url:paginate:newer_older",
            self.paginate_newer_older
        )

    def current_url(self) -> str:
        """The URL of the request currently being served."""

        return self.internal_url(
            cherrypy.request.script_name +
            cherrypy.request.path_info,
            cherrypy.request.params
        )

    @staticmethod
    def internal_url(
            path: typing.Optional[str] = None,
            query: typing.Optional[typing.Dict[str, typing.Any]] = None,
            force_querystring: bool = False,
            trailing_slash: bool = False
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

        url = f"{scheme}{hostname}{path or cherrypy.request.script_name}"

        if trailing_slash and not url.endswith("/"):
            url += "/"

        if query:
            query = {
                key: value
                for (key, value) in query.items()
                if value
            }

        if force_querystring:
            url = f"{url}?"

        if query:
            url = f"{url}?{urlencode(query)}"

        request_headers = cherrypy.request.headers
        use_https = request_headers.get("X-Https", "") == "On"

        if not use_https:
            use_https = request_headers.get("X-Forwarded-Proto", "") == "https"

        if use_https:
            url = f"https:{url.split(':', 1).pop()}"

        return url

    def alt_url(self, url: str) -> str:
        """Convert an external URL to the equivalent in the alturl app."""

        if not url.startswith("http"):
            url = f"//{url}"

        parsed_url = urlparse(url)

        return self.internal_url(
            f"/alturl/{parsed_url.netloc}{parsed_url.path}"
        )

    @staticmethod
    def readable_url(url: str) -> str:
        """Convert a URL to a form suitable for bare display."""

        readable_url = url.replace("https://", "")
        readable_url = readable_url.replace("http://", "")
        readable_url = readable_url.split('#', 1)[0]
        return readable_url

    def paginate_newer_older(
            self,
            params: typing.Dict[str, typing.Any],
            per_page: int = 10,
            offset: int = 0,
            total: int = 0
    ) -> typing.Tuple[typing.Optional[str], typing.Optional[str]]:
        """Determine the next-page and previous-page URLs for paginated
        records presented in reverse chronological order.

        """

        newer_url = None
        older_url = None

        older_offset = per_page + offset
        newer_offset = offset - per_page

        if older_offset < total:
            params["offset"] = older_offset
            older_url = self.internal_url(query=params)

        if newer_offset >= 0:
            params["offset"] = newer_offset
            newer_url = self.internal_url(query=params)

        return (newer_url, older_url)
