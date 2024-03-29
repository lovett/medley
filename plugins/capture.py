"""Store HTTP requests and responses for later review"""

import json
import sqlite3
from typing import Any
from typing import Optional
from typing import List
from typing import Tuple
from typing import cast
import cherrypy
from . import mixins


class Plugin(cherrypy.process.plugins.SimplePlugin, mixins.Sqlite):
    """A CherryPy plugin for capturing HTTP requests."""

    def __init__(self, bus: cherrypy.process.wspbus.Bus) -> None:
        cherrypy.process.plugins.SimplePlugin.__init__(self, bus)

        self.db_path = self._path("captures.sqlite")

    def setup(self) -> None:
        """Create the database."""

        self._create("""
        PRAGMA journal_mode=WAL;

        CREATE TABLE IF NOT EXISTS captures (
            request_uri, request_line, request, response,
            created DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS index_request_uri
            ON captures(request_uri);

        """)

    def start(self) -> None:
        """Define the CherryPy messages to listen for.

        This plugin owns the capture prefix.
        """
        self.bus.subscribe("server:ready", self.setup)
        self.bus.subscribe("capture:add", self.add)
        self.bus.subscribe("capture:search", self.search)
        self.bus.subscribe("capture:get", self.get)
        self.bus.subscribe("capture:prune", self.prune)

    def add(self,
            request: Any,
            response: Any) -> bool:
        """Store a single HTTP request and response pair.

        This is usually invoked from the capture Cherrypy tool.

        """

        if not hasattr(request, "json"):
            request.json = None

        request_bundle = {
            "headers": request.headers,
            "params": request.body.params,
            "json": request.json
        }

        response_bundle = {
            "status": response.status
        }

        request_uri_parts = request.request_line.split(" ")

        request_uri = " ".join(request_uri_parts[1:-1])

        self._execute(
            """INSERT INTO captures
            (request_uri, request_line, request, response)
            VALUES (?, ?, ?, ?)""",
            (
                request_uri,
                request.request_line,
                json.dumps(request_bundle),
                json.dumps(response_bundle)
            )
        )

        return True

    def search(
            self,
            path: Optional[str] = None,
            offset: int = 0,
            limit: int = 10
    ) -> Tuple[int, List[sqlite3.Row]]:
        """Locate previously stored requests by path."""

        search_clause = ""
        if path:
            search_clause = "AND request_uri=?"

        sql = f"""SELECT rowid, request_line,
        request as 'request [json]',
        response as 'response [json]',
        created as 'created [local_datetime]',
        (SELECT count(*) FROM captures WHERE 1=1 {search_clause})
        as total
        FROM captures
        WHERE 1=1 {search_clause}
        ORDER BY rowid DESC
        LIMIT ? OFFSET ?"""  # nosec

        if path:
            result = self._select(sql, (path, path, limit, offset))
        else:
            result = self._select(sql, (limit, offset))

        count = 0
        if result:
            count = result[0]["total"]

        return (count, result)

    def get(self, rowid: int) -> Optional[sqlite3.Row]:
        """Locate previously stored requests by ID."""

        sql = """SELECT rowid, request_line, request as 'request [json]',
        response as 'response [json]',
        created as 'created [timestamp]'
        FROM captures
        WHERE rowid=?"""

        return cast(
            Optional[sqlite3.Row],
            self._selectOne(sql, (rowid,))
        )

    def prune(self, cutoff_months: int = 3) -> None:
        """Delete old records.

        This is normally invoked from the maintenance plugin, and
        restricts the growth of the captures database since old
        records are unlikely to be useful.

        """

        deletion_count = self._delete(
            """DELETE FROM captures
            WHERE strftime('%s', created) < strftime('%s', 'now', ?)""",
            (f"-{cutoff_months} month",)
        )

        unit = "row" if deletion_count == 1 else "rows"

        cherrypy.engine.publish(
            "applog:add",
            "capture:prune",
            f"{deletion_count} {unit} deleted"
        )
