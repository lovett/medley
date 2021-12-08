"""File storage."""

import mimetypes
from pathlib import Path
import typing
import cherrypy
from pydantic import BaseModel
from pydantic import ValidationError
from pydantic import Field


class GetParams(BaseModel):
    """Valid request parameters for GET requests."""
    path: Path


class PutParams(BaseModel):
    """Valid request parameters for PUT requests."""
    storage_path: Path
    content_type: str = Field(
        "",
        strip_whitespace=True,
        to_lower=True,
    )
    content: cherrypy._cpreqbody.Part

    class Config:
        """Custom model configuration."""
        arbitrary_types_allowed = True


class Controller:
    """Dispatch application requests based on HTTP verb."""

    show_on_homepage = True
    exposed = True

    @cherrypy.tools.etag()
    def GET(self, *args: str) -> typing.Union[bytes, typing.Iterator[bytes]]:
        """Dispatch to a subhandler based on the URL path."""

        path = Path(*args)

        try:
            params = GetParams(path=path)
        except ValidationError as error:
            raise cherrypy.HTTPError(400) from error

        if params.path.as_posix() != ".":
            return self.serve_file(params)

        return self.index()

    @staticmethod
    def PUT(
            *args: str,
            content_type: str = "application/octet-stream",
            content: cherrypy._cpreqbody.Part
    ) -> None:
        """Accept a file for storage."""

        try:
            params = PutParams(
                storage_path=Path(*args),
                content_type=content_type,
                content=content,
            )
        except ValidationError as error:
            raise cherrypy.HTTPError(400) from error

        if not params.content_type:
            guessed_type, _ = mimetypes.guess_type(
                params.storage_path.as_posix()
            )

            if guessed_type:
                params.content_type = guessed_type

        cherrypy.engine.publish(
            "warehouse:remove",
            params.storage_path
        )

        while True:
            data = params.content.file.read(8192)

            if not data:
                break

            cherrypy.engine.publish(
                "warehouse:add:chunk",
                path=params.storage_path,
                content_type=params.content_type,
                chunk=typing.cast(bytes, data)
            )

        cherrypy.response.status = 204

    @staticmethod
    def serve_file(params: GetParams) -> typing.Iterator[bytes]:
        """Send back a previously-stored file."""

        content_type = cherrypy.engine.publish(
            "warehouse:get:type",
            params.path
        ).pop()

        if not content_type:
            content_type = "application/octet-stream"

        cherrypy.response.stream = True
        cherrypy.response.headers["Content-Type"] = content_type

        return cherrypy.engine.publish(
            "warehouse:get:chunks",
            params.path
        ).pop()

    @staticmethod
    def index() -> bytes:
        """List all available files."""

        files = cherrypy.engine.publish(
            "warehouse:list"
        ).pop()

        return cherrypy.engine.publish(
            "jinja:render",
            "apps/warehouse/warehouse-list.jinja.html",
            files=files,
        ).pop()
