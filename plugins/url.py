"""Work out an app URL from a controller instance."""

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
    def internal_url(path=None, query=()):
        """Create an absolute internal URL."""

        # A non-root path is treated as a sub-path of the current app.
        if path and not path.startswith("/"):
            path = "{}/{}".format(cherrypy.request.script_name, path)

        url = "{}{}".format(
            cherrypy.request.base,
            path or cherrypy.request.script_name
        )

        if query:
            url = "{}?{}".format(url, urlencode(query))

        if cherrypy.request.headers.get("X-Https", "") == "On":
            url = "https:{}".format(url.split(":", 1).pop())

        return url
