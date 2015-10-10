import os.path
import sqlite3
import cherrypy
import util.sqlite_converters

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
        request_dict = {
            "headers": request.headers,
            "params": request.body.params
        }

        try:
            request_dict["json"] = request.json
        except:
            request_dict["json"] = None

            request_pickle = pickle.dumps(request_dict)

        response_dict = {
            "status": response.status
        }

        response_pickle = pickle.dumps(response_dict)

        sql = "INSERT INTO captures (request_line, request, response) VALUES (?, ?, ?)"
        self.cur.execute(sql, (request.request_line,
                               sqlite3.Binary(request_pickle),
                               sqlite3.Binary(response_pickle)))

        insert_id = cur.lastrowid
        self.conn.commit()
        return insert_id

    def find(self, request_line=None, limit=10):
        sql = """SELECT id, request_line, request as 'request [pickle]',
        response as 'response [pickle]', created as 'created [created]'
        FROM captures
        WHERE request_line LIKE ?
        ORDER BY created DESC
        LIMIT ?"""

        if request_line:
            request_line_filter = "%{}%".format(request_line)
        else:
            request_line_filter = "%"

        self.cur.execute(sql, (request_line_filter, limit))

        return self.cur.fetchall()
