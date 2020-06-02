"""Serve static assets."""

import mimetypes
from pathlib import Path
import typing
import cherrypy


class Controller:
    """Dispatch application requests based on HTTP verb."""

    show_on_homepage = False
    exposed = True

    @cherrypy.tools.etag()
    @staticmethod
    def GET(*args: str, **_kwargs: str) -> bytes:
        """Serve static assets from the filesystem.

        This is an alternative to CherryPy's staticdir tool that
        provides flexibility around how files are read."""

        app_path = ("apps", "static",) + args
        asset = Path(*app_path)

        asset_bytes = typing.cast(
            bytes,
            cherrypy.engine.publish(
                "filesystem:read",
                asset
            ).pop()
        )

        if asset_bytes == b"":
            raise cherrypy.HTTPError(404)

        mime_type, _ = mimetypes.guess_type(asset.name)

        if not mime_type:
            mime_type = "application/octet-stream"

        cherrypy.response.headers["Content-Type"] = mime_type

        return asset_bytes
