"""Determine if a file should be linted."""

import os.path
import cherrypy


class Controller:
    """Dispatch application requests based on HTTP verb."""

    exposed = True
    show_on_homepage = False

    @staticmethod
    def GET(*args, **_kwargs) -> bytes:
        """Determine if a file should be linted."""

        target_path = "/".join(args)

        if not os.path.exists(target_path):
            raise cherrypy.HTTPError(404)

        current_hash = cherrypy.engine.publish(
            "hasher:file",
            target_path
        ).pop()

        stored_hash = cherrypy.engine.publish(
            "cache:get",
            f"lintable:{target_path}"
        ).pop()

        if current_hash == stored_hash:
            return "no".encode()

        return "yes".encode()

    @staticmethod
    def PUT(*args, **_kwargs) -> None:
        """Request storage of a file's current hash."""
        target_path = "/".join(args)

        if not os.path.exists(target_path):
            raise cherrypy.HTTPError(400)

        current_hash = cherrypy.engine.publish(
            "hasher:file",
            target_path
        ).pop()

        cherrypy.engine.publish(
            "cache:set",
            f"lintable:{target_path}",
            current_hash,
            86400 * 365
        )

        cherrypy.response.status = 204
