"""Review HTTP requests and responses"""

import cherrypy


class Controller:
    """Dispatch application requests based on HTTP verb."""

    exposed = True
    show_on_homepage = True

    @cherrypy.tools.capture()
    @cherrypy.tools.provides(formats=("html",))
    def GET(self, *args: str, **kwargs: str) -> bytes:
        """Dispatch GET requests to a subhandler based on the URL path."""

        if "status" in args:
            return self.capture(*args, **kwargs)

        if "path" in kwargs:
            return self.search(*args, **kwargs)

        if args:
            return self.show(int(args[0]))

        return self.index()

    def POST(self, *args: str, **kwargs: str) -> bytes:
        """Dispatch POST requests to a subhandler based on the URL path."""

        if "status" in args:
            return self.capture(*args, **kwargs)

        raise cherrypy.NotFound()

    def PUT(self, *args: str, **kwargs: str) -> bytes:
        """Dispatch PUT requests to a subhandler based on the URL path."""

        if "status" in args:
            return self.capture(*args, **kwargs)

        raise cherrypy.NotFound()

    def DELETE(self, *args: str, **kwargs: str) -> bytes:
        """Dispatch DELETE requests to a subhandler based on the URL path."""

        if "status" in args:
            return self.capture(*args, **kwargs)

        raise cherrypy.NotFound()

    @staticmethod
    def index(*_args: str, **kwargs: str) -> bytes:
        """List captures in reverse-chronological order."""

        per_page = 20
        offset = int(kwargs.get("offset", 0))

        (total_records, captures) = cherrypy.engine.publish(
            "capture:search",
            offset=offset,
            limit=per_page
        ).pop()

        pagination_url = cherrypy.engine.publish(
            "url:internal",
            "/captures"
        ).pop()

        response: bytes = cherrypy.engine.publish(
            "jinja:render",
            "apps/captures/captures.jinja.html",
            captures=captures,
            total_records=total_records,
            per_page=per_page,
            offset=offset,
            pagination_url=pagination_url
        ).pop()

        return response

    @staticmethod
    def search(*_args: str, **kwargs: str) -> bytes:
        """Locate captures by request path."""

        per_page = 20
        offset = int(kwargs.get("offset", 0))
        path = kwargs.get("path", "").strip()
        subview_title = path

        (total_records, captures) = cherrypy.engine.publish(
            "capture:search",
            path=path,
            offset=offset,
            limit=per_page
        ).pop()

        pagination_url = cherrypy.engine.publish(
            "url:internal",
            "/captures",
            {"path": path}
        ).pop()

        response: bytes = cherrypy.engine.publish(
            "jinja:render",
            "apps/captures/captures.jinja.html",
            captures=captures,
            total_records=total_records,
            per_page=per_page,
            offset=offset,
            path=path,
            pagination_url=pagination_url,
            subview_title=subview_title
        ).pop()

        return response

    @staticmethod
    def show(rowid: int) -> bytes:
        """Display a single capture."""

        capture = cherrypy.engine.publish(
            "capture:get",
            rowid
        ).pop()

        response: bytes = cherrypy.engine.publish(
            "jinja:render",
            "apps/captures/captures.jinja.html",
            captures=(capture,),
            subview_title=rowid
        ).pop()

        return response

    @staticmethod
    def capture(*args: str, **_kwargs: str) -> bytes:
        """Capture a request and return the status code indicated by the
        URL.

        """

        try:
            status = int(args[1])
        except ValueError:
            status = 404
        except IndexError:
            status = 200

        if 400 <= status <= 500:
            raise cherrypy.HTTPError(status)

        if 300 <= status <= 308:
            destination = cherrypy.engine.publish(
                "url:internal",
                "/"
            ).pop()

            raise cherrypy.HTTPRedirect(destination, status)

        return str(status).encode()
