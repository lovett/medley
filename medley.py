import cherrypy
import os.path
import os
import sys
import pwd

class MedleyServer(object):
    @cherrypy.expose
    def index(self):
        return "hello"

    @cherrypy.expose
    def ip(self, token=""):

        ip = None
        for header in ["X-REAL-IP", "REMOTE-ADDR"]:
            try:
                ip = cherrypy.request.headers[header]
            except KeyError:
                pass

        if not ip:
            raise cherrypy.HTTPError(400, "Unable to determine IP")

        if not token:
            return ip

        host = cherrypy.request.app.config["ip_tokens"].get(token)

        if not host:
            raise cherrypy.HTTPError(404, "Unrecognized token")

        try:
            dnsCommand = cherrypy.request.app.config["ip_dns"].get("command")
            dnsCommand[dnsCommand.find("$ip")] = ip
            dnsCommand[dnsCommand.find("$host")] = host
            cherrypy._cpcompat_subprocess.call(dnsCommand);
        except ValueError:
            pass
        finally:
            return "ok"

if __name__ == "__main__":
    appRoot = os.path.dirname(os.path.abspath(__file__))
    appConfig = os.path.join(appRoot, "medley.conf")
    cherrypy.config.update(appConfig)

    # attempt to drop privileges if daemonized
    user = cherrypy.config.get("server.user")
    if user:
        try:
            account = pwd.getpwnam(user)
            cherrypy.process.plugins.DropPrivileges(cherrypy.engine, umask=0o022, uid=account.pw_uid, gid=account.pw_gid).subscribe()
        except KeyError:
            cherrypy.log.error("Unable to look up the user '{}'. Not dropping privileges.".format(user), "APP")
            pass

    daemonize = cherrypy.config.get("server.daemonize")
    if daemonize:
        cherrypy.config.update({'log.screen': False})
        cherrypy.process.plugins.Daemonizer(cherrypy.engine).subscribe()

    pidFile = cherrypy.config.get("server.pid")
    if pidFile:
        cherrypy.process.plugins.PIDFile(cherrypy.engine, pidFile).subscribe()

    cherrypy.quickstart(MedleyServer(), "/", appConfig)
