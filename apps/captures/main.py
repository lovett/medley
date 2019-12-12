"""Display previously-captured requests."""

import cherrypy


class Controller:
    """Dispatch application requests based on HTTP verb."""

    name = "Captures"
    exposed = True
    show_on_homepage = True

    @staticmethod
    @cherrypy.tools.negotiable()
    def GET(*_args, **kwargs):
        """Display a list of recent captures, or captures matching a URI path.
        """

        path = kwargs.get('path')
        cid = kwargs.get('cid')
        offset = int(kwargs.get('offset', 0))
        per_page = 5

        if path:
            path = path.strip()

        if cid:
            captures = cherrypy.engine.publish(
                "capture:get",
                int(cid)
            ).pop()
            newer_url = None
            older_url = None
        else:
            total, captures = cherrypy.engine.publish(
                "capture:search",
                path,
                offset,
                limit=per_page
            ).pop()

            (newer_url, older_url) = cherrypy.engine.publish(
                "url:paginate:newer_older",
                params={"path": path},
                per_page=per_page,
                offset=offset,
                total=total
            ).pop()

        return {
            "html": ("captures.jinja.html", {
                "path": path,
                "captures": captures,
                "newer_url": newer_url,
                "older_url": older_url,
            })
        }
