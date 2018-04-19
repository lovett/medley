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
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_line, request, response,
            created DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS index_request_line
            on captures(request_line);

        """)

    def start(self):
        self.bus.subscribe("capture:add", self.add)
        self.bus.subscribe("capture:search", self.search)
        self.bus.subscribe("capture:recent", self.recent)

    def stop(self):
        pass

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

        sql = """INSERT INTO captures
        (request_line, request, response)
        VALUES (?, ?, ?)"""

        placeholder_values = (
            request.request_line,
            sqlite3.Binary(request_bin),
            sqlite3.Binary(response_bin)
        )

        self._insert(sql, [placeholder_values])

        return True

    def search(self, search, limit=20):
        sql = """SELECT id, request_line, request as 'request [binary]',
        response as 'response [binary]', created as 'created [datetime]'
        FROM captures
        WHERE request_line LIKE ?
        ORDER BY created DESC
        LIMIT ?"""

        search_sql = "%{}%".format(search)

        return self._select(sql, (search_sql, limit))

    def recent(self, limit=50):
        sql = """SELECT id, request_line, request as 'request [binary]',
        response as 'response [binary]', created as 'created [datetime]'
        FROM captures
        ORDER BY created DESC
        LIMIT ?"""

        return self._select(sql, (limit,))
