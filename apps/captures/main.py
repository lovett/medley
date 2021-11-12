"""Review HTTP requests and responses"""

from enum import Enum
import cherrypy
from pydantic import BaseModel
from pydantic import ValidationError
from pydantic import Field


class Actions(str, Enum):
    """Valid keywords for the first URL segment of this application."""
    NONE = ""
    STATUS = "status"
    PATH = "path"
    SHOW = "show"


class StatusParams(BaseModel):
    """Base class for status URLs across all HTTP verbs."""
    status: int = 0
    action: Actions = Actions.NONE


class GetParams(StatusParams):
    """Valid request parameters for GET requests."""
    per_page: int = 20
    offset: int = 0
    path: str = Field("", strip_whitespace=True, min_length=1, to_lower=True)
    uid: int = Field(0, gt=-1)


class PostParams(StatusParams):
    """Valid request parameters for POST requests."""
    ...


class PutParams(StatusParams):
    """Valid request parameters for POST requests."""
    ...


class DeleteParams(StatusParams):
    """Valid request parameters for POST requests."""
    ...


class Controller:
    """Dispatch application requests based on HTTP verb."""

    exposed = True
    show_on_homepage = True

    @cherrypy.tools.capture()
    @cherrypy.tools.provides(formats=("html",))
    def GET(self, action: str = "", uid: str = "0", **kwargs: str) -> bytes:
        """Dispatch GET requests to a subhandler based on the URL path."""

        try:
            params = GetParams(action=action, uid=uid, **kwargs)
        except ValidationError as error:
            raise cherrypy.HTTPError(400) from error

        if params.action == Actions.STATUS:
            cherrypy.response.status = self.capture(params)
            return str(cherrypy.response.status).encode()

        if params.path:
            return self.search(params)

        if params.action == Actions.SHOW:
            return self.show(params)

        return self.index(params)

    @cherrypy.tools.capture()
    def POST(self, action: str = "", **kwargs: str) -> bytes:
        """Dispatch POST requests to a subhandler based on the URL path."""

        try:
            params = PostParams(action=action, **kwargs)
        except ValidationError as error:
            raise cherrypy.HTTPError(400) from error

        if params.action == Actions.STATUS:
            cherrypy.response.status = self.capture(params)
            return str(cherrypy.response.status).encode()

        raise cherrypy.NotFound()

    @cherrypy.tools.capture()
    def PUT(self, action: str = "", **kwargs: str) -> bytes:
        """Dispatch PUT requests to a subhandler based on the URL path."""

        try:
            params = PutParams(action=action, **kwargs)
        except ValidationError as error:
            raise cherrypy.HTTPError(400) from error

        if params.action == Actions.STATUS:
            cherrypy.response.status = self.capture(params)
            return str(cherrypy.response.status).encode()

        raise cherrypy.NotFound()

    @cherrypy.tools.capture()
    def DELETE(self, action: str = "", **kwargs: str) -> bytes:
        """Dispatch DELETE requests to a subhandler based on the URL path."""

        try:
            params = DeleteParams(action=action, **kwargs)
        except ValidationError as error:
            raise cherrypy.HTTPError(400) from error

        if params.action == Actions.STATUS:
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
            path=params.path,
            offset=params.offset,
            limit=params.per_page
        ).pop()

        pagination_url = cherrypy.engine.publish(
            "app_url",
            "/captures",
            {"path": params.path}
        ).pop()

        response: bytes = cherrypy.engine.publish(
            "jinja:render",
            "apps/captures/captures.jinja.html",
            captures=captures,
            total_records=total_records,
            per_page=params.per_page,
            offset=params.offset,
            path=params.path,
            pagination_url=pagination_url,
            subview_title=params.path
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
