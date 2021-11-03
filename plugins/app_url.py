"""Work out an app URL from a controller instance."""

import typing
import cherrypy
from resources.url import Url


class Plugin(cherrypy.process.plugins.SimplePlugin):
    """A CherryPy plugin for building app-specific URLs."""

    def __init__(self, bus: cherrypy.process.wspbus.Bus) -> None:
        cherrypy.process.plugins.SimplePlugin.__init__(self, bus)

    def start(self) -> None:
        """Define the CherryPy messages to listen for.

        This plugin owns the app_url prefix.
        """
        self.bus.subscribe("app_url", self.app_url)

    @staticmethod
    def app_url(
            path: str = "",
            query: typing.Optional[typing.Dict[str, typing.Any]] = None,
    ) -> str:
        """Build an absolute internal URL."""

        base = cherrypy.request.base

        headers = cherrypy.request.headers
        if headers.get("X-Forwarded-Proto", "").lower() == "https":
            base = base.replace("http://", "https://")

        if Url(base).is_loopback():
            base = ""

        if not base:
            base = cherrypy.engine.publish(
                "registry:first:value",
                "config:base_url"
            ).pop()

        # A non-root path is treated as a sub-path of the current app.
        if not path.startswith("/"):
            path = f"{cherrypy.request.script_name}/{path}"

        # Trailing slash enforcement.
        if not any((path.endswith("/"), "?" in path, "." in path)):
            path += "/"

        return Url(f"{base}{path}", query=query).address
