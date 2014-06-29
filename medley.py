import cherrypy
import sqlite3
import os.path
import subprocess
import sys
import pwd

class Medley(object):
    def getCursor(self, config):
        db = sqlite3.connect(config['filename'])
        cur = db.cursor()

        cur.execute("CREATE TABLE IF NOT EXISTS ipinform (token TEXT, hostname TEXT)")
        cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_ipinform_token ON ipinform (token)")
        db.commit()

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

        cur.execute("SELECT hostname FROM ipinform WHERE token=?", (token,))
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
    user = pwd.getpwnam("medley")
    cherrypy.engine.autoreload.unsubscribe()
    cherrypy.process.plugins.DropPrivileges(cherrypy.engine, uid=user.pw_uid, gid=user.pw_gid).subscribe()
    cherrypy.tree.mount(Medley())
