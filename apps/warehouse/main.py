"""File storage."""

import mimetypes
from pathlib import Path
from typing import Iterator
from typing import Union
import cherrypy


class Controller:
    """Dispatch application requests based on HTTP verb."""

    show_on_homepage = True
    exposed = True

    def DELETE(self, *args: str) -> None:
        """Discard a previously-uploaded file."""

        path = Path(*args)

        cherrypy.engine.publish(
            "warehouse:remove",
            path
        ).pop()

        self.clear_etag()

        cherrypy.response.status = 204

    @cherrypy.tools.etag()
    def GET(
            self,
            *args: str,
            **kwargs: str
    ) -> Union[bytes, Iterator[bytes]]:
        """Dispatch to a subhandler based on the URL path."""

        path = Path(*args)

        if path.as_posix() != ".":
            return self.serve_file(path)

        return self.index(**kwargs)

    def POST(
            self,
            *,
            storage_path: str = "",
            content: cherrypy._cpreqbody.Part
    ) -> None:
        """Accept a file for storage."""

        if not content.file:
            redirect_url = cherrypy.engine.publish(
                "app_url",
                "",
                {"failure": "nofile"}
            ).pop()
            raise cherrypy.HTTPRedirect(redirect_url)

        destination = Path(storage_path)
        content_type = "application/octet-stream"
        guessed_type, _ = mimetypes.guess_type(
            destination.as_posix()
        )

        if guessed_type:
            content_type = guessed_type

        if destination.as_posix() == ".":
            destination = Path(
                content.filename.lower().replace(" ", "-")
            )

        self.ingest_file(content, destination, content_type)

        redirect_url = cherrypy.engine.publish(
            "app_url",
            "",
            {"added": destination.as_posix()}
        ).pop()
        raise cherrypy.HTTPRedirect(redirect_url)

    def PUT(
            self,
            *args: str,
            content_type: str = "application/octet-stream",
            content: cherrypy._cpreqbody.Part
    ) -> None:
        """Accept a file for storage."""

        destination = Path(*args)

        if not content_type:
            guessed_type, _ = mimetypes.guess_type(
                destination.as_posix()
            )

            if guessed_type:
                content_type = guessed_type

        self.ingest_file(content, destination, content_type)

    def ingest_file(
            self,
            content: cherrypy._cpreqbody.Part,
            destination: Path,
            content_type: str
    ) -> None:
        """Storage of a newly-uploaded file."""

        cherrypy.engine.publish(
            "warehouse:remove",
            destination
        )

        while True:
            data: bytes = content.file.read(8192)

            if not data:
                break

            cherrypy.engine.publish(
                "warehouse:add:chunk",
                path=destination,
                content_type=content_type,
                chunk=data
            )

        self.clear_etag()
        cherrypy.response.status = 204

    @staticmethod
    def serve_file(path: Path) -> Iterator[bytes]:
        """Send back a previously-stored file."""

        content_type = cherrypy.engine.publish(
            "warehouse:get:type",
            path
        ).pop()

        if not content_type:
            content_type = "application/octet-stream"

        cherrypy.response.stream = True
        cherrypy.response.headers["Content-Type"] = content_type

        return cherrypy.engine.publish(
            "warehouse:get:chunks",
            path
        ).pop()

    @staticmethod
    def index(**kwargs: str) -> bytes:
        """List all available files."""

        added = kwargs.get("added", "").strip()
        failure = kwargs.get("failure", "")

        files = cherrypy.engine.publish(
            "warehouse:list"
        ).pop()

        app_url = cherrypy.engine.publish(
            "app_url"
        ).pop()

        upload_url = cherrypy.engine.publish(
            "app_url",
        ).pop()

        return cherrypy.engine.publish(
            "jinja:render",
            "apps/warehouse/warehouse-list.jinja.html",
            files=files,
            added_file=added,
            failure=failure,
            upload_url=upload_url,
            app_url=app_url
        ).pop()

    @staticmethod
    def clear_etag() -> None:
        """Drop the current etag for the index page."""
        mount_point = __package__.split(".").pop()

        cherrypy.engine.publish(
            "memorize:clear",
            f"etag:/{mount_point}"
        )
