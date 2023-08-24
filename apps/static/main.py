"""Serve static assets."""

from pathlib import Path
import cherrypy


class Controller:
    show_on_homepage = False
    exposed = True

    @staticmethod
    @cherrypy.tools.etag()
    def GET(*args: str, **_kwargs: str) -> bytes:
        """Serve static assets from the filesystem.

        This is an alternative to CherryPy's staticdir tool that
        provides flexibility around how files are read."""

        if args[0] == "templates":
            raise cherrypy.HTTPError(404)

        app_path = ("apps", "static",) + args
        asset_path = Path(*app_path)

        asset_bytes, asset_mime = cherrypy.engine.publish(
            "assets:get",
            asset_path
        ).pop()

        if asset_bytes == b"":
            raise cherrypy.HTTPError(404)

        cherrypy.response.headers["Content-Type"] = asset_mime

        return asset_bytes
