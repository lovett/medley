"""Determine if a file should be linted."""

import os.path
import cherrypy


class Controller:
    """Dispatch application requests based on HTTP verb."""

    exposed = True
    show_on_homepage = False

    @staticmethod
    def GET(*args, **_kwargs) -> bytes:
        target_path = "/".join(args)

        if not os.path.exists(target_path):
            raise cherrypy.HTTPError(404)

        current_checksum = cherrypy.engine.publish(
            "checksum:file",
            target_path
        ).pop()

        stored_checksum = cherrypy.engine.publish(
            "cache:get",
            f"lintable:{target_path}"
        ).pop()

        print(stored_checksum)

        if current_checksum == stored_checksum:
            return "no".encode()

        return "yes".encode()

    @staticmethod
    def PUT(*args, **_kwargs) -> None:
        target_path = "/".join(args)

        if not os.path.exists(target_path):
            raise cherrypy.HTTPError(400)

        current_checksum = cherrypy.engine.publish(
            "checksum:file",
            target_path
        ).pop()

        cherrypy.engine.publish(
            "cache:set",
            f"lintable:{target_path}",
            current_checksum,
            86400 * 365
        )

        cherrypy.response.status = 204
