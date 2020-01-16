"""
Interact with Google AppEngine.

See https://googleapis.dev/python/storage/latest/client.html
"""

import json
import pathlib
import typing
import urllib.parse
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

    @staticmethod
    def full_storage_path(path: pathlib.Path) -> pathlib.Path:
        """Get an absolute path to a file within the storage root."""

        storage_root = cherrypy.engine.publish(
            "registry:first:value",
            "config:storage_root",
            as_path=True
        ).pop()

        return typing.cast(pathlib.Path, storage_root / path)

    def ingest_file(
            self,
            storage_path: pathlib.Path,
            batch_size: int = 100
    ) -> None:
        """Match a log file to a processor based on its file path."""

        request_top_path = ("appengine.googleapis.com", "request_log")

        if not storage_path.parts[0:2] == request_top_path:
            return

        extras_path = pathlib.Path("stdout").joinpath(*storage_path.parts[2:])

        line_count = self.process_request_log(storage_path, batch_size)

        self.process_application_log(extras_path, batch_size)

        unit = "line" if line_count == 1 else "lines"

        cherrypy.engine.publish(
            "applog:add",
            "gcp_appengine",
            f"{line_count} {unit} ingested"
        )

        cherrypy.engine.publish("scheduler:add", 5, "logindex:parse")

    @decorators.log_runtime
    def process_application_log(
            self,
            storage_path: pathlib.Path,
            batch_size: int = 100
    ) -> None:
        """Add the lines of an hourly application log in JSON format to the
        logindex database.
        """

        log_path = self.full_storage_path(storage_path)

        if not log_path.is_file():
            print("application log does not exist")
            return

        batch: typing.List[typing.Any] = []

        with open(log_path, "r") as file_handle:
            while True:
                line = file_handle.readline()
                if not line:
                    break

                json_line = json.loads(line)

                payload = json_line.get("textPayload")

                if not payload:
                    continue

                # Handle payloads that aren't key-value pairs.
                pairs = {
                    "message": payload.replace('"', "'")
                }

                if "=" in payload:
                    pairs = {
                        key: value[0].replace('"', "'")
                        for key, value
                        in urllib.parse.parse_qs(payload).items()
                    }

                if "trace" not in pairs:
                    continue

                record_hash = pairs["trace"].split("/")[0]
                batch.append((
                    record_hash,
                    self.pairs_to_extras(pairs)
                ))

                if len(batch) > batch_size:
                    self.publish_extras(batch)
                    batch = []

        if batch:
            self.publish_extras(batch)
            batch = []

    @decorators.log_runtime
    def process_request_log(
            self,
            storage_path: pathlib.Path,
            batch_size: int = 100
    ) -> int:
        """
        Add the lines of an hourly request log in JSON format to the
        logindex database.

        This is similar to the ingestion process for log files in
        combined format, even though it means additional parsing
        (going from JSON to combined here, and then parsing combined
        back down to individual fields in the logindex plugin). Doing
        it this way reduces duplication with the logindex plugin.
        """

        log_path = self.full_storage_path(storage_path)

        if not log_path.is_file():
            return 0

        line_count = 0
        batch: typing.List[typing.Any] = []
        with open(log_path, "r") as file_handle:
            while True:
                line = file_handle.readline()

                if not line:
                    break

                offset = file_handle.tell()

                json_line = json.loads(line)

                payload = json_line.get("protoPayload")

                if not payload:
                    continue

                combined_line = self.json_to_combined(payload)

                record_hash = payload.get("traceId")
                if not record_hash:
                    record_hash = cherrypy.engine.publish(
                        "hasher:md5",
                        line
                    ).pop()

                batch.append((
                    str(storage_path),
                    offset,
                    record_hash,
                    combined_line
                ))

                if len(batch) > batch_size:
                    line_count += self.publish_lines(batch)
                    batch = []
        if batch:
            line_count += self.publish_lines(batch)
            batch = []

        return line_count

    @staticmethod
    def combined_quoted(value: str = None) -> str:
        """Wrap a value in quotes unless it is empty."""

        if value:
            quoteless_value = value.replace('"', '[DOUBLEQUOTE]')
            return f'"{quoteless_value}"'

        return "-"

    @staticmethod
    def combined_pair(key: str, value: str = None) -> str:
        """Pair a key and its quoted value or suppress both."""

        if value:
            quoteless_value = value.replace('"', '[DOUBLEQUOTE]')
            return f'{key}="{quoteless_value}"'
        return ""

    def json_to_combined(self, payload: typing.Any) -> str:
        """Format a JSON-formatted string in combined log format."""

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
            self.combined_quoted(resource),
            str(payload["status"]),
            payload.get("responseSize", "0"),
            self.combined_quoted(payload.get("referrer")),
            self.combined_quoted(payload.get("userAgent")),
            self.combined_quoted(payload.get("host")),
            self.combined_pair("latency", payload.get("latency")),
            self.combined_pair("end_time", payload.get("endTime")),
            self.combined_pair("version", payload.get("versionId")),
            self.combined_pair("request_id", payload.get("requestId"))
        )

        return " ".join(fields).strip()

    def pairs_to_extras(self, pairs: typing.Dict[str, str]) -> str:
        """Format a dict as a quoted key-value string."""

        quoted_pairs = [
            self.combined_pair(key, value)
            for key, value
            in pairs.items()
        ]

        return " ".join(quoted_pairs)

    @staticmethod
    def publish_lines(batch: typing.Iterable[str]) -> int:
        """Send a batch of request logs in combined format to the logindex
        plugin.

        """
        result = cherrypy.engine.publish(
            "logindex:insert_line",
            batch
        ).pop()

        return typing.cast(int, result)

    @staticmethod
    def publish_extras(batch: typing.List[typing.Tuple[str, str]]) -> None:
        """Append extra name-value fields a previously-saved combined log."""

        cherrypy.engine.publish(
            "logindex:append_line",
            batch
        )
