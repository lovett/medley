"""
Interact with Google AppEngine.

See https://googleapis.dev/python/storage/latest/client.html
"""

import json
import pathlib
import typing
import cherrypy
import pendulum
from . import decorators


class Plugin(cherrypy.process.plugins.SimplePlugin):
    """A CherryPy plugin for interacting with Google Appengine."""

    def __init__(self, bus: cherrypy.process.wspbus.Bus) -> None:
        cherrypy.process.plugins.SimplePlugin.__init__(self, bus)

    def start(self) -> None:
        """Define the CherryPy messages to listen for.

        This plugin owns the gcp prefix.
        """

        self.bus.subscribe(
            "gcp:appengine:ingest_file",
            self.ingest_file
        )

    @decorators.log_runtime
    def ingest_file(
            self,
            log_path: pathlib.Path,
            batch_size: int = 100
    ) -> None:
        """
        Add the lines of an hourly request log in JSON format to the
        logindex database.

        This is similar to the ingestion process for log files in
        combined format, even though it means additional parsing
        (going from JSON to combined here, and then parsing combined
        back down to individual fields in the logindex plugin). Doing
        it this way reduces duplication with the logindex plugin.
        """

        bucket_root = cherrypy.engine.publish(
            "registry:first_value",
            "config:bucket_root",
            as_path=True
        ).pop()

        if not log_path.is_file():
            return

        source_file = log_path.relative_to(bucket_root)

        line_count = 0
        batch: typing.List[typing.Any] = []
        with open(log_path, "r") as file_handle:
            while True:
                line = file_handle.readline()

                if not line:
                    break

                offset = file_handle.tell()

                combined_line = self.json_to_combined(line)

                batch.append((
                    str(source_file),
                    offset,
                    cherrypy.engine.publish("hasher:md5", line).pop(),
                    combined_line
                ))

                if len(batch) > batch_size:
                    line_count += self.publish_batch(batch)
                    batch = []
        if batch:
            line_count += self.publish_batch(batch)
            batch = []

        cherrypy.engine.publish("scheduler:add", 5, "logindex:parse")

        cherrypy.engine.publish(
            "applog:add",
            "gcp_appengine",
            "lines_ingested",
            line_count
        )

    @staticmethod
    def combined_quoted(value: str = None) -> str:
        """Wrap a value in quotes unless it is empty."""
        if value:
            return f'"{value}"'

        return "-"

    @staticmethod
    def combined_pair(key: str, value: str = None) -> str:
        """Pair a key and its quoted value or suppress both."""
        if value:
            return f'{key}="{value}"'
        return ""

    def json_to_combined(self, line: str) -> str:
        """Format a JSON-formatted string in combined log format."""
        json_line = json.loads(line)

        payload = json_line.get("protoPayload")

        line = payload.get("line")
        message = ""
        if line:
            message = line[0].get("logMessage", "")

        resource = " ".join((
            payload["method"],
            payload["resource"],
            payload["httpVersion"]
        ))

        timestamp = pendulum.parse(
            payload["startTime"]
        ).format("DD/MMM/YYYY:HH:mm:ss:SSSSSS ZZ")

        fields = (
            payload["ip"],
            "-",
            "-",
            f'[{timestamp}]',
            f'"{resource}"',
            str(payload["status"]),
            payload.get("responseSize", "0"),
            self.combined_quoted(payload.get("referrer")),
            self.combined_quoted(payload.get("userAgent")),
            self.combined_quoted(payload.get("host")),
            self.combined_pair("latency", payload.get("latency")),
            self.combined_pair("end_time", payload.get("endTime")),
            self.combined_pair("version", payload.get("versionId")),
            self.combined_pair("request_id", payload.get("requestId")),
            message
        )

        return " ".join(fields).strip()

    @staticmethod
    def publish_batch(batch) -> int:
        """Send a batch of logs in combined format to the logindex plugin."""

        result = cherrypy.engine.publish(
            "logindex:insert_line",
            batch
        ).pop()

        return typing.cast(int, result)
