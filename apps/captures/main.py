"""HTTP traffic database"""

import cherrypy


class Controller:
    exposed = True
    show_on_homepage = True

    @cherrypy.tools.capture()
    @cherrypy.tools.provides(formats=("html",))
    def GET(self,
            uid: str = "",
            subresource: str = "",
            **kwargs: str
    ) -> bytes:
        """Dispatch GET requests to a subhandler based on the URL path."""

        per_page = int(kwargs.get("per_page", 20))
        offset = int(kwargs.get("offset", 0))
        q = kwargs.get("q", "").lower()
        status = int(kwargs.get("status", 0))

        try:
            record_id = int(uid or 0)
        except ValueError as exc:
            raise cherrypy.HTTPError(400, "Invalid uid") from exc

        if subresource == "status":
            cherrypy.response.status = self.capture(status)
            return str(cherrypy.response.status).encode()

        if q:
            return self.search(q, per_page, offset)

        if subresource == "show":
            return self.show(record_id)

        return self.index(per_page, offset)

    @cherrypy.tools.capture()
    def POST(self, subresource: str = "", **kwargs: str) -> bytes:
        """Dispatch POST requests to a subhandler based on the URL path."""

        status = int(kwargs.get("status", 0))

        if subresource == "status":
            cherrypy.response.status = self.capture(status)
            return str(cherrypy.response.status).encode()

        raise cherrypy.NotFound()

    @cherrypy.tools.capture()
    def PUT(self, subresource: str = "", **kwargs: str) -> bytes:
        """Dispatch PUT requests to a subhandler based on the URL path."""

        status = int(kwargs.get("status", 0))

        if subresource == "status":
            cherrypy.response.status = self.capture(status)
            return str(cherrypy.response.status).encode()

        raise cherrypy.NotFound()

    @cherrypy.tools.capture()
    def DELETE(self, subresource: str = "", **kwargs: str) -> bytes:
        """Dispatch DELETE requests to a subhandler based on the URL path."""

        status = int(kwargs.get("status", 0))

        if subresource == "status":
            cherrypy.response.status = self.capture(status)
            return str(cherrypy.response.status).encode()

        raise cherrypy.NotFound()

    @staticmethod
    def capture(status: int) -> int:
        """Capture a request and return the status code indicated by the
        URL.

        """

        if 400 <= status <= 500:
            raise cherrypy.HTTPError(status)

        if 300 <= status <= 308:
            destination = cherrypy.engine.publish(
                "app_url",
                "/"
            ).pop()

            raise cherrypy.HTTPRedirect(destination, status)

        return status

    @staticmethod
    def index(per_page: int, offset: int) -> bytes:
        """List captures in reverse-chronological order."""

        (total_records, captures) = cherrypy.engine.publish(
            "capture:search",
            offset=offset,
            limit=per_page
        ).pop()

        pagination_url = cherrypy.engine.publish(
            "app_url",
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
    def search(q: str, per_page: int, offset: int) -> bytes:
        """Locate captures by request path."""

        (total_records, captures) = cherrypy.engine.publish(
            "capture:search",
            path=q,
            offset=offset,
            limit=per_page
        ).pop()

        pagination_url = cherrypy.engine.publish(
            "app_url",
            "/captures",
            {"q": q}
        ).pop()

        response: bytes = cherrypy.engine.publish(
            "jinja:render",
            "apps/captures/captures.jinja.html",
            captures=captures,
            total_records=total_records,
            per_page=per_page,
            offset=offset,
            q=q,
            pagination_url=pagination_url,
            subview_title=q
        ).pop()

        return response

    @staticmethod
    def show(record_id: int) -> bytes:
        """Display a single capture."""

        capture = cherrypy.engine.publish(
            "capture:get",
            record_id
        ).pop()

        response: bytes = cherrypy.engine.publish(
            "jinja:render",
            "apps/captures/captures.jinja.html",
            captures=(capture,),
            subview_title=record_id
        ).pop()

        return response
