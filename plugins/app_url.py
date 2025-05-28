"""Work out an app URL from a controller instance."""

from typing import Any
from typing import Dict
from typing import Optional
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
        self.bus.subscribe("app_url:base", self.base_url)

    @staticmethod
    def base_url() -> str:
        """Determine the root URL of the application."""
        base = cherrypy.request.base

        headers = cherrypy.request.headers
        if headers.get("X-Forwarded-Proto", "").lower() == "https":
            base = base.replace("http://", "https://")

        if not base:
            base = cherrypy.engine.publish(
                "registry:first:value",
                "config:base_url"
            ).pop()

        return base

    def app_url(
            self,
            path: str = "",
            query: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Build an absolute internal URL."""

        base = self.base_url()

        # A non-root path is treated as a sub-path of the current app.
        if not path.startswith("/"):
            path = f"{cherrypy.request.script_name}{cherrypy.request.path_info}{path}"

        # Trailing slash enforcement.
        if not any((path.endswith("/"), "?" in path, "." in path)):
            path += "/"

        return Url(f"{base}{path}", query=query).address
