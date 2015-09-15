import sys
import os.path
sys.path.append("../../")

import cherrypy
import tools.negotiable
import tools.jinja
import util.net

class Controller:
    """Display the the requester's address and the server's external address"""

    exposed = True

    user_facing = True

    def POST(self, token=None):
        host = cherrypy.request.app.config["ip_tokens"].get(token)
        if not host:
            raise cherrypy.HTTPError(400, "Invalid token")

        dns_command = cherrypy.config.get("ip.dns.command")[:]
        if dns_command:
            dns_command[dns_command.index("$ip")] = ip_address
            dns_command[dns_command.index("$host")] = host
            subprocess.call(dns_command)

        if cherrypy.request.as_text:
            return "ok"
        else:
            return { "result": "ok" }

    @cherrypy.tools.template(template="ip.html")
    @cherrypy.tools.negotiable()
    def GET(self):
        ip_address = None
        for header in ("X-Real-Ip", "Remote-Addr"):
            try:
                ip_address = cherrypy.request.headers[header]
                break
            except KeyError:
                pass

        if not ip_address:
            raise cherrypy.HTTPError(400, "Unable to determine IP")

        external_ip = util.net.externalIp()
        if cherrypy.request.as_text:
            return ip_address
        else:
            return {
                "address": ip_address,
                "external_ip": external_ip
            }
