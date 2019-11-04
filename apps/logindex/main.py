"""Trigger indexing of log files."""

import os.path
import pathlib
import typing
import pendulum
import cherrypy


class Controller:
    """Dispatch application requests based on HTTP verb."""

    exposed = True
    user_facing = False

    def POST(self, *args, **kwargs):
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

            channel: typing.Optional[str] = None
            if url_path == "bucket/gcp/appengine":
                channel = "gcp:appengine:ingest_file"

            if channel:
                self.index_by_file(path, channel)
                cherrypy.response.status = 204
                return

        cherrypy.response.status = 404

    def index_by_date(self, start: str, end: str) -> None:
        """
        Index logs in combined format based on a date range.
        """

        start_date = self.parse_log_date(start, None)
        end_date = self.parse_log_date(end, start_date)

        if not start_date:
            raise cherrypy.HTTPError(400, "Invalid start")

        if start_date > end_date:
            raise cherrypy.HTTPError(400, "Invalid range")

        cherrypy.engine.publish("logindex:enqueue", start_date, end_date)

    @staticmethod
    def index_by_file(path: str, channel: str) -> None:
        """Index a log file by its path.

        The channel argument dictates how the indexing will
        occur. Unlike date-based indexing, there is no expectation
        that the file will be in combined format.
        """

        storage_root = typing.cast(
            pathlib.Path,
            cherrypy.engine.publish(
                "registry:first_value",
                "config:storage_root",
                as_path=True
            ).pop()
        )

        try:
            bucket_path = storage_root.joinpath(path)
            bucket_path.relative_to(storage_root)
        except ValueError:
            raise cherrypy.HTTPError(400, "Invalid path")

        if not bucket_path.is_file():
            raise cherrypy.HTTPError(400, "Path is not a file")

        cherrypy.engine.publish(channel, bucket_path)

    @staticmethod
    def parse_log_date(val, default: typing.Any) -> typing.Any:

        """
        Convert a date string in either date or filename format
        to a datetime.

        Date format is YYYY-mm-dd. Filename format is the same, but with
        a file extension at the end.
        """

        try:
            filename = os.path.splitext(val)[0]
            return pendulum.from_format(filename, "YYYY-MM-DD")
        except (TypeError, ValueError):
            return default
