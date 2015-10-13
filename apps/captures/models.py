import os.path
import sqlite3
import cherrypy
import util.sqlite_converters
import pickle

class CaptureManager:
    conn = None
    cur = None

    def __init__(self):
        db_dir = cherrypy.config.get("database_dir")
        path = os.path.join(db_dir, "captures.sqlite")
        sql = None
        if not os.path.isfile(path):
            sql = """
            CREATE TABLE IF NOT EXISTS captures (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_line, request, response,
            created DEFAULT CURRENT_TIMESTAMP
            )"""
        sqlite3.register_converter("created", util.sqlite_converters.convert_date)
        sqlite3.register_converter("pickle", util.sqlite_converters.convert_pickled)
        self.conn = sqlite3.connect(path, detect_types=sqlite3.PARSE_COLNAMES)
        self.conn.row_factory = sqlite3.Row
        self.cur = self.conn.cursor()

        if sql:
            self.cur.executescript(sql)
            self.conn.commit()

    def __del__(self):
        if self.conn:
            self.conn.close()

    def add(self, request, response):
        request_pickle = pickle.dumps({
            "headers": request.headers,
            "params": request.body.params,
            "json": request.json
        })

        response_pickle = pickle.dumps({
            "status": response.status
        })

        sql = "INSERT INTO captures (request_line, request, response) VALUES (?, ?, ?)"
        self.cur.execute(sql, (request.request_line,
                               sqlite3.Binary(request_pickle),
                               sqlite3.Binary(response_pickle)))

        insert_id = self.cur.lastrowid
        self.conn.commit()
        return insert_id

    def search(self, search, limit=20):
        sql = """SELECT id, request_line, request as 'request [pickle]',
        response as 'response [pickle]', created as 'created [created]'
        FROM captures
        WHERE request_line LIKE ?
        ORDER BY created DESC
        LIMIT ?"""

        search_sql = "%{}%".format(search)

        self.cur.execute(sql, (search_sql, limit))

        return self.cur.fetchall()

    def recent(self, limit=50):
        sql = """SELECT id, request_line, request as 'request [pickle]',
        response as 'response [pickle]', created as 'created [created]'
        FROM captures
        ORDER BY created DESC
        LIMIT ?"""

        self.cur.execute(sql, (limit,))

        return self.cur.fetchall()
