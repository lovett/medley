"""Store HTTP requests and responses for later review"""

import msgpack
import cherrypy
import sqlite3
from . import mixins


class Plugin(cherrypy.process.plugins.SimplePlugin, mixins.Sqlite):

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
        self.bus.subscribe("capture:add", self.add)
        self.bus.subscribe("capture:search", self.search)
        self.bus.subscribe("capture:get", self.get)

    def add(self, request, response):
        """Store a single HTTP request and response pair

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

    def search(self, path=None, offset=0, limit=20):
        if path:
            search_clause = "AND request_uri=?"
            placeholders = (path, path, limit, offset)
        else:
            search_clause = ""
            placeholders = (limit, offset)

        # Annoyingly, the count query must use the same converters
        # as the main query in spite of the null values.
        sql = """SELECT 0 as rowid, count(*) as request_line,
        null as 'request [binary]',
        null as 'response [binary]', null as 'created [datetime]'
        FROM captures WHERE 1=1 {search_clause}
        UNION
        SELECT rowid, request_line, request as 'request [binary]',
        response as 'response [binary]',
        created as 'created [datetime]'
        FROM captures
        WHERE 1=1 {search_clause}
        ORDER BY rowid DESC
        LIMIT ? OFFSET ?""".format(search_clause=search_clause)

        result = self._select(sql, placeholders)

        # Because the query is ordered by rowid, the row with the
        # count is last.
        count = result[-1]["request_line"]

        return (count, result[0:-1])

    def get(self, capture_id):
        sql = """SELECT rowid, request_line, request as 'request [binary]',
        response as 'response [binary]',
        created as 'created [datetime]'
        FROM captures
        WHERE rowid=?"""

        return self._select(sql, (capture_id,))
