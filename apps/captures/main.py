"""Display previously-captured requests."""

import cherrypy


class Controller:
    """Dispatch application requests based on HTTP verb."""

    name = "Captures"

    @cherrypy.tools.negotiable()
    def GET(self, path=None, cid=None, offset=0):
        """Display a list of recent captures, or captures matching a URI path.
        """

        if cid:
            captures = cherrypy.engine.publish(
                "capture:get",
                int(cid)
            ).pop()
            older_offset = None
            newer_offset = None
        else:
            total, captures = cherrypy.engine.publish(
                "capture:search",
                path,
                offset
            ).pop()

            older_offset = len(captures) + offset
            if older_offset >= total:
                older_offset = None

            newer_offset = offset - len(captures)
            if newer_offset <= 0:
                newer_offset = None

        return {
            "html": ("captures.html", {
                "path": path,
                "captures": captures,
                "newer_offset": newer_offset,
                "older_offset": older_offset,
                "app_name": self.name
            })
        }
