"""Trigger indexing of log files."""

from datetime import date, datetime
import pathlib
from typing import Optional
import cherrypy
from pydantic import BaseModel
from pydantic import Field
from pydantic import ValidationError
import pytz


class PostParams(BaseModel):
    """Parameters for POST requests."""
    start: date
    end: Optional[date]
    origin: str = Field("", strip_whitespace=True)
    path: str = Field("", strip_whitespace=True)


class Controller:
    """Dispatch application requests based on HTTP verb."""

    exposed = True
    show_on_homepage = False

    def POST(self, *args: str, **kwargs: str) -> None:
        """Dispatch to a subhandler based on the URL path."""

        try:
            params = PostParams(
                origin="/".join(args[1:]),
                **kwargs
            )
        except ValidationError as error:
            raise cherrypy.HTTPError(400) from error

        if params.start:
            self.index_by_date(params)
            cherrypy.response.status = 204
            return

        if params.origin == "gcp/appengine":
            self.index_by_gcp_file(params)
            cherrypy.response.status = 204
            return

        cherrypy.response.status = 404

    @staticmethod
    def index_by_date(params: PostParams) -> None:
        """Index logs in combined format based on a date range."""

        start_date = datetime(
            params.start.year,
            params.start.month,
            params.start.day,
            0,
            0,
            tzinfo=pytz.timezone("UTC")
        )

        end_date = start_date
        if params.end:
            end_date = datetime(
                params.end.year,
                params.end.month,
                params.end.day,
                0,
                0,
                tzinfo=pytz.timezone("UTC")
            )

        if start_date > end_date:
            raise cherrypy.HTTPError(400, "Invalid range")

        cherrypy.engine.publish(
            "logindex:enqueue",
            start_date,
            end_date
        )

    @staticmethod
    def index_by_gcp_file(params: PostParams) -> None:
        """Index a GCP log file by its path."""

        storage_root = cherrypy.engine.publish(
            "registry:first:value",
            "config:storage_root",
            as_path=True
        ).pop()

        try:
            # Is the file within the storage root?
            bucket_path = storage_root.joinpath(params.path)
            bucket_path.relative_to(storage_root)
        except ValueError as err:
            raise cherrypy.HTTPError(400, "Invalid path") from err

        if not bucket_path.is_file():
            raise cherrypy.HTTPError(400, "Path is not a file")

        cherrypy.engine.publish(
            "gcp:appengine:ingest_file",
            pathlib.Path(params.path)
        )
