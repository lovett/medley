import cherrypy
import sqlite3
import os.path
import subprocess

class Medley(object):
    def setup(self):
        con = sqlite3.connect(os.path.dirname(__file__) + "/medley.db")
        cur = con.cursor()

        cur.execute("CREATE TABLE IF NOT EXISTS iplog (token TEXT, hostname TEXT)")
        cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_iplog_token ON iplog (token)")
        return con

    @cherrypy.expose
    def index(self):
        return "hello"

    @cherrypy.expose
    def iplog(self, token=""):

        if not token:
            return "fail"

        con = self.setup()

        cur = con.cursor()

        if "X-Real-IP" in cherrypy.request.headers:
            ip = cherrypy.request.headers["X-REAL-IP"]
        else:
            ip = cherrypy.request.headers["REMOTE-ADDR"]

        cur.execute("SELECT hostname FROM iplog WHERE token=?", (token,))
        row = cur.fetchone()

        if (row):
            subprocess.call(["pdnsd-ctl", "add", "a", ip, row[0]]);
        con.close()

        return "ok"


if __name__ == '__main__':
    configFile = os.path.join(os.path.dirname(__file__), 'config.py')
    cherrypy.quickstart(Medley(), config=configFile)
else:
    cherrypy.tree.mount(Medley())
