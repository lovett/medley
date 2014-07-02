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

if __name__ == '__main__':
    pwd = os.path.dirname(os.path.abspath(__file__))
    conf = os.path.join(pwd, 'medley.conf')
    cherrypy.quickstart(MedleyServer(), config=conf)
#else:
    #user = pwd.getpwnam("medley")
    #cherrypy.engine.autoreload.unsubscribe()
    #cherrypy.process.plugins.DropPrivileges(cherrypy.engine, uid=user.pw_uid, gid=user.pw_gid).subscribe()
    #app = cherrypy.tree.mount(MedleyServer())
    #os.makedirs("/var/log/medley", exist_ok=True)
