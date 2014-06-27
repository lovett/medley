import cherrypy
import sqlite3
import os.path
import subprocess
import sys

class Medley(object):
    def getCursor(self, config):
        db = sqlite3.connect(config['filename'])
        cur = db.cursor()

        cur.execute("CREATE TABLE IF NOT EXISTS ipinform (token TEXT, hostname TEXT)")
        cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_ipinform_token ON iplog (token)")

        return cur

    @cherrypy.expose
    def index(self):
        return "hello"

    @cherrypy.expose
    def ipinform(self, token=""):

        if not token:
            raise cherrypy.HTTPError(400, "Token not specified")

        cur = self.getCursor(cherrypy.request.app.config['db'])

        if "X-Real-IP" in cherrypy.request.headers:
            ip = cherrypy.request.headers["X-REAL-IP"]
        else:
            ip = cherrypy.request.headers["REMOTE-ADDR"]

        cur.execute("SELECT hostname FROM iplog WHERE token=?", (token,))
        row = cur.fetchone()

        if (row):
            subprocess.call(["pdnsd-ctl", "add", "a", ip, row[0]]);
            return "ok"
        else:
            raise cherrypy.HTTPError(400, "Invalid token")


if __name__ == '__main__':
    pwd = os.path.dirname(os.path.abspath(__file__))
    conf = os.path.join(pwd, 'medley.conf')
    cherrypy.quickstart(Medley(), config=conf)
else:
    cherrypy.tree.mount(Medley())
