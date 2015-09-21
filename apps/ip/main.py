import sys
import os.path
sys.path.append("../../")

import subprocess
import cherrypy
import tools.negotiable
import tools.jinja
import util.net
import IPy

class Controller:
    """Display the the requester's address and the server's external address"""

    exposed = True

    user_facing = True

    def validateIp(self, value):
        try:
            IPy.IP(value)
            return True
        except:
            return False


    def ipFromHeader(self, headers):
        for header in ("X-Real-Ip", "Remote-Addr"):
            if header in headers:
                return cherrypy.request.headers[header]
        return None


    def PUT(self, token=None):
        host = cherrypy.config["ip.tokens"].get(token)
        if not host:
            raise cherrypy.HTTPError(400, "Invalid token")

        try:
            dns_command = cherrypy.config.get("ip.dns.command")[:]
        except TypeError:
            cherrypy.response.status = 404
            return

        dns_command[dns_command.index("$ip")] = self.ipFromHeader(cherrypy.request.headers)
        dns_command[dns_command.index("$host")] = host
        subprocess.call(dns_command)
        cherrypy.response.status = 201

    @cherrypy.tools.template(template="ip.html")
    @cherrypy.tools.negotiable()
    def GET(self):
        ip_address = self.ipFromHeader(cherrypy.request.headers)

        if not self.validateIp(ip_address):
            raise cherrypy.HTTPError(400, "Unable to determine IP")

        external_ip = util.net.externalIp()
        if cherrypy.request.as_text:
            return ip_address
        else:
            return {
                "address": ip_address,
                "external_ip": external_ip
            }
