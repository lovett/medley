"""Display previously-captured requests."""

import cherrypy


class Controller:
    """Dispatch application requests based on HTTP verb."""

    exposed = True
    show_on_homepage = True

    @staticmethod
    @cherrypy.tools.provides(formats=("html",))
    def GET(*args, **kwargs) -> bytes:
        """Display a list of recent captures, or captures matching a URI path.

        """

        rowid = None
        if args:
            rowid = args[0]

        path = kwargs.get('path')
        offset = int(kwargs.get('offset', 0))
        per_page = 5
        subview_title = ""

        if path:
            path = path.strip()

        if rowid:
            captures = cherrypy.engine.publish(
                "capture:get",
                int(rowid)
            ).pop()
            newer_url = None
            older_url = None
            subview_title = rowid
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

        return cherrypy.engine.publish(
            "jinja:render",
            "captures.jinja.html",
            path=path,
            captures=captures,
            newer_url=newer_url,
            older_url=older_url,
            subview_title=subview_title
        ).pop()
