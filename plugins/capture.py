"""Store HTTP requests and responses for later review"""

import sqlite3
import msgpack
import cherrypy
from . import mixins


class Plugin(cherrypy.process.plugins.SimplePlugin, mixins.Sqlite):
    """A CherryPy plugin for capturing HTTP requests."""

    def __init__(self, bus):
        cherrypy.process.plugins.SimplePlugin.__init__(self, bus)

        self.db_path = self._path("captures.sqlite")

        self._create("""
        CREATE TABLE IF NOT EXISTS captures (
            request_uri, request_line, request, response,
            created DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS index_request_uri
            on captures(request_uri);
        """)

    def start(self):
        """Define the CherryPy messages to listen for.

        This plugin owns the capture prefix.
        """
        self.bus.subscribe("capture:add", self.add)
        self.bus.subscribe("capture:search", self.search)
        self.bus.subscribe("capture:get", self.get)

    def add(self, request, response):
        """Store a single HTTP request and response pair.

        This is usually invoked from the capture Cherrypy tool.

        """

        if not hasattr(request, "json"):
            request.json = None

        request_bin = msgpack.packb({
            "headers": request.headers,
            "params": request.body.params,
            "json": request.json
        }, use_bin_type=True)

        response_bin = msgpack.packb({
            "status": response.status
        }, use_bin_type=True)

        request_uri_parts = request.request_line.split(' ')

        request_uri = " ".join(request_uri_parts[1:-1])

        placeholder_values = (
            request_uri,
            request.request_line,
            sqlite3.Binary(request_bin),
            sqlite3.Binary(response_bin)
        )

        self._insert("""INSERT INTO captures
        (request_uri, request_line, request, response)
        VALUES (?, ?, ?, ?)""", [placeholder_values])

        return True

    def search(self, path=None, offset=0, limit=10):
        """Locate previously stored requests by path."""

        if path:
            search_clause = "AND request_uri=?"
            placeholders = (path, path, limit, offset)
        else:
            search_clause = ""
            placeholders = (limit, offset)

        sql = """SELECT rowid, request_line,
        request as 'request [binary]',
        response as 'response [binary]',
        created as 'created [datetime]',
        (SELECT count(*) FROM captures WHERE 1=1 {search_clause})
        as total
        FROM captures
        WHERE 1=1 {search_clause}
        ORDER BY rowid DESC
        LIMIT ? OFFSET ?""".format(search_clause=search_clause)

        result = self._select(sql, placeholders)

        if result:
            count = result[0]["total"]
        else:
            count = 0

        return (count, result)

    def get(self, capture_id):
        """Locate previously stored requests by ID."""

        sql = """SELECT rowid, request_line, request as 'request [binary]',
        response as 'response [binary]',
        created as 'created [datetime]'
        FROM captures
        WHERE rowid=?"""

        return self._select(sql, (capture_id,))
