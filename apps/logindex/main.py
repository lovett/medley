"""Trigger indexing of log files."""

from datetime import datetime
import pathlib
import pytz
import cherrypy


class Controller:
    exposed = True
    show_on_homepage = False

    def POST(self, **kwargs: str) -> None:
        """Dispatch to a subhandler based on the URL path."""

        start = kwargs.get("start", "")
        end = kwargs.get("end", start)
        origin = kwargs.get("origin", "").strip()
        path = kwargs.get("path", "").strip()

        if start:
            self.index_by_date(start, end)
            cherrypy.response.status = 204
            return

        if origin == "gcp/appengine":
            self.index_by_gcp_file(path)
            cherrypy.response.status = 204
            return

        cherrypy.response.status = 404

    @staticmethod
    def index_by_date(start: str, end: str) -> None:
        """Index logs in combined format based on a date range."""

        fmt = "%Y-%m-%d"

        try:
            start_date = datetime.strptime(f"{start}", fmt)
            start_date = start_date.replace(tzinfo=pytz.timezone("UTC"))
        except ValueError as exc:
            raise cherrypy.HTTPError(400, "Bad format for start") from exc

        try:
            end_date = datetime.strptime(f"{end}", fmt)
            end_date = end_date.replace(tzinfo=pytz.timezone("UTC"))
        except ValueError as exc:
            raise cherrypy.HTTPError(400, "Bad format for end") from exc

        if start_date > end_date:
            raise cherrypy.HTTPError(400, "Invalid start/end range")

        cherrypy.engine.publish(
            "logindex:enqueue",
            start_date,
            end_date
        )

    @staticmethod
    def index_by_gcp_file(path: str) -> None:
        """Index a GCP log file by its path."""

        storage_root = cherrypy.engine.publish(
            "registry:first:value",
            "config:storage_root",
            as_path=True
        ).pop()

        try:
            # Is the file within the storage root?
            bucket_path = storage_root.joinpath(path)
            bucket_path.relative_to(storage_root)
        except ValueError as exc:
            raise cherrypy.HTTPError(400, "Invalid path") from exc

        if not bucket_path.is_file():
            raise cherrypy.HTTPError(400, "Path is not a file")

        cherrypy.engine.publish(
            "gcp:appengine:ingest_file",
            pathlib.Path(path)
        )
