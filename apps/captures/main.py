"""Display previously-captured requests."""

import cherrypy


class Controller:
    """Dispatch application requests based on HTTP verb."""

    name = "Captures"

    @staticmethod
    @cherrypy.tools.negotiable()
    def GET(*_args, **kwargs):
        """Display a list of recent captures, or captures matching a URI path.
        """

        path = kwargs.get('path', '')
        cid = kwargs.get('cid')
        offset = int(kwargs.get('offset', 0))

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
            "html": ("captures.jinja.html", {
                "path": path,
                "captures": captures,
                "newer_offset": newer_offset,
                "older_offset": older_offset,
            })
        }
