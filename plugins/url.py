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
        self.bus.subscribe("url:for_controller", self.url_for_controller)

    @staticmethod
    def url_for_controller(controller, path=None, query=()):
        """Create a URL for an application given its controller."""

        host = cherrypy.request.headers.get("Host", "")

        if cherrypy.request.headers.get("X-Https", "") == "On":
            proto = "https"
        else:
            proto = "http"

        url = next(
            ("{}://{}{}".format(proto, host, key)
             for key in cherrypy.tree.apps
             if isinstance(cherrypy.tree.apps[key].root, type(controller))),
            None
        )

        if path:
            url = "{}/{}".format(url, path)

        if query:
            url = "{}?{}".format(url, urlencode(query))

        return url
