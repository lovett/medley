"""Review HTTP requests and responses"""

from enum import Enum
import cherrypy
from pydantic import BaseModel
from pydantic import ValidationError
from pydantic import Field


class Subresource(str, Enum):
    """Valid keywords for the second URL path segment of this application."""
    NONE = ""
    STATUS = "status"
    SHOW = "show"


class StatusParams(BaseModel):
    """Base class for status URLs across all HTTP verbs."""
    status: int = 0
    subresource: Subresource = Subresource.NONE


class GetParams(StatusParams):
    """Parameters for GET requests."""
    per_page: int = 20
    offset: int = 0
    q: str = Field("", strip_whitespace=True, min_length=1, to_lower=True)
    uid: int = Field(0, gt=-1)


class PostParams(StatusParams):
    """Parameters for POST requests."""
    ...


class PutParams(StatusParams):
    """Parameters for PUT requests."""
    ...


class DeleteParams(StatusParams):
    """Parameters for DELETE requests."""
    ...


class Controller:
    """Dispatch application requests based on HTTP verb."""

    exposed = True
    show_on_homepage = True

    @cherrypy.tools.capture()
    @cherrypy.tools.provides(formats=("html",))
    def GET(
            self,
            uid: str = "0",
            subresource: str = "",
            **kwargs: str
    ) -> bytes:
        """Dispatch GET requests to a subhandler based on the URL path."""

        try:
            params = GetParams(subresource=subresource, uid=uid, **kwargs)
        except ValidationError as error:
            raise cherrypy.HTTPError(400) from error

        if params.subresource == Subresource.STATUS:
            cherrypy.response.status = self.capture(params)
            return str(cherrypy.response.status).encode()

        if params.q:
            return self.search(params)

        if params.subresource == Subresource.SHOW:
            return self.show(params)

        return self.index(params)

    @cherrypy.tools.capture()
    def POST(self, subresource: str = "", **kwargs: str) -> bytes:
        """Dispatch POST requests to a subhandler based on the URL path."""

        try:
            params = PostParams(subresource=subresource, **kwargs)
        except ValidationError as error:
            raise cherrypy.HTTPError(400) from error

        if params.subresource == Subresource.STATUS:
            cherrypy.response.status = self.capture(params)
            return str(cherrypy.response.status).encode()

        raise cherrypy.NotFound()

    @cherrypy.tools.capture()
    def PUT(self, subresource: str = "", **kwargs: str) -> bytes:
        """Dispatch PUT requests to a subhandler based on the URL path."""

        try:
            params = PutParams(subresource=subresource, **kwargs)
        except ValidationError as error:
            raise cherrypy.HTTPError(400) from error

        if params.subresource == Subresource.STATUS:
            cherrypy.response.status = self.capture(params)
            return str(cherrypy.response.status).encode()

        raise cherrypy.NotFound()

    @cherrypy.tools.capture()
    def DELETE(self, subresource: str = "", **kwargs: str) -> bytes:
        """Dispatch DELETE requests to a subhandler based on the URL path."""

        try:
            params = DeleteParams(subresource=subresource, **kwargs)
        except ValidationError as error:
            raise cherrypy.HTTPError(400) from error

        if params.subresource == Subresource.STATUS:
            cherrypy.response.status = self.capture(params)
            return str(cherrypy.response.status).encode()

        raise cherrypy.NotFound()

    @staticmethod
    def capture(params: StatusParams) -> int:
        """Capture a request and return the status code indicated by the
        URL.

        """

        if 400 <= params.status <= 500:
            raise cherrypy.HTTPError(params.status)

        if 300 <= params.status <= 308:
            destination = cherrypy.engine.publish(
                "app_url",
                "/"
            ).pop()

            raise cherrypy.HTTPRedirect(destination, params.status)

        return params.status

    @staticmethod
    def index(params: GetParams) -> bytes:
        """List captures in reverse-chronological order."""

        (total_records, captures) = cherrypy.engine.publish(
            "capture:search",
            offset=params.offset,
            limit=params.per_page
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
            per_page=params.per_page,
            offset=params.offset,
            pagination_url=pagination_url
        ).pop()

        return response

    @staticmethod
    def search(params: GetParams) -> bytes:
        """Locate captures by request path."""

        (total_records, captures) = cherrypy.engine.publish(
            "capture:search",
            path=params.q,
            offset=params.offset,
            limit=params.per_page
        ).pop()

        pagination_url = cherrypy.engine.publish(
            "app_url",
            "/captures",
            {"q": params.q}
        ).pop()

        response: bytes = cherrypy.engine.publish(
            "jinja:render",
            "apps/captures/captures.jinja.html",
            captures=captures,
            total_records=total_records,
            per_page=params.per_page,
            offset=params.offset,
            q=params.q,
            pagination_url=pagination_url,
            subview_title=params.q
        ).pop()

        return response

    @staticmethod
    def show(params: GetParams) -> bytes:
        """Display a single capture."""

        capture = cherrypy.engine.publish(
            "capture:get",
            params.uid
        ).pop()

        response: bytes = cherrypy.engine.publish(
            "jinja:render",
            "apps/captures/captures.jinja.html",
            captures=(capture,),
            subview_title=params.uid
        ).pop()

        return response
