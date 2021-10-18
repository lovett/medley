"""Trigger indexing of log files."""

import os.path
import pathlib
import cherrypy


class Controller:
    """Dispatch application requests based on HTTP verb."""

    exposed = True
    show_on_homepage = False

    def POST(self, *args: str, **kwargs: str) -> None:
        """
        Dispatch to a subhandler.
        """

        if not args:
            start = kwargs.get("start", "")
            end = kwargs.get("end", "")

            self.index_by_date(start, end)
            cherrypy.response.status = 204
            return

        if args[0] == "bucket":
            url_path = "/".join(args)
            path = kwargs.get("path", "")

            if url_path == "bucket/gcp/appengine":
                self.index_by_gcp_file(path)
                cherrypy.response.status = 204
                return

        cherrypy.response.status = 404

    @staticmethod
    def index_by_date(start: str, end: str) -> None:
        """Index logs in combined format based on a date range."""

        start_base, _ = os.path.splitext(start)
        start_date = cherrypy.engine.publish(
            "clock:from_format",
            start_base,
            "%Y-%m-%d"
        ).pop()

        if not start_date:
            raise cherrypy.HTTPError(400, "Invalid start")

        end_date = start_date
        if end:
            end_base, _ = os.path.splitext(end)
            end_date = cherrypy.engine.publish(
                "clock:from_format",
                end_base,
                "%Y-%m-%d"
            ).pop()

        if not end_date:
            raise cherrypy.HTTPError(400, "Invalid end")

        if start_date > end_date:
            raise cherrypy.HTTPError(400, "Invalid range")

        cherrypy.engine.publish("logindex:enqueue", start_date, end_date)

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
        except ValueError as err:
            raise cherrypy.HTTPError(400, "Invalid path") from err

        if not bucket_path.is_file():
            raise cherrypy.HTTPError(400, "Path is not a file")

        storage_path = pathlib.Path(path)
        cherrypy.engine.publish("gcp:appengine:ingest_file", storage_path)
