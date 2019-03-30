"""Work out an app URL from a controller instance."""

import ipaddress
from urllib.parse import urlencode
import cherrypy
from cherrypy.process import plugins


class Plugin(plugins.SimplePlugin):
    """A CherryPy plugin for building app-specific URLs."""

    def __init__(self, bus):
        plugins.SimplePlugin.__init__(self, bus)

    def start(self):
        """Define the CherryPy messages to listen for.

        This plugin owns the url prefix.
        """
        self.bus.subscribe("url:internal", self.internal_url)

    @staticmethod
    def internal_url(path=None, query=(), trailing_slash=False):
        """Create an absolute internal URL.

        The URL hostname is sourced from two places. Most of the time,
        there will be an incoming request at hand and
        cherrypy.request.base will hold the desired value.

        If there isn't an incoming request, fall back to a value
        stored in the registry.

        """

        hostname = cherrypy.request.base

        try:
            if ipaddress.ip_address(hostname).is_loopback:
                hostname = None
        except ValueError:
            pass

        if not hostname:
            hostname = cherrypy.engine.publish(
                "registry:first_value",
                "config:base_url"
            ).pop()

        # A non-root path is treated as a sub-path of the current app.
        if path and not path.startswith("/"):
            path = "{}/{}".format(cherrypy.request.script_name, path)

        url = "{}{}".format(
            hostname,
            path or cherrypy.request.script_name
        )

        if trailing_slash and not url.endswith("/"):
            url += "/"

        if query:
            url = "{}?{}".format(url, urlencode(query))

        request_headers = cherrypy.request.headers
        use_https = request_headers.get("X-Https", "") == "On"

        if not use_https:
            use_https = request_headers.get("X-Forwarded-Proto", "") == "https"

        if use_https:
            url = "https:{}".format(url.split(":", 1).pop())

        return url
