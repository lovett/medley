import subprocess
import cherrypy
import util.net
import util.cache
import apps.registry.models
import ipaddress

class Controller:
    """Determine the current IP address"""

    name = "IP"

    exposed = True

    user_facing = True

    @cherrypy.tools.template(template="ip.html")
    @cherrypy.tools.negotiable()
    def GET(self):
        client_ip = self.ipFromHeader(cherrypy.request.headers)

        try:
            ipaddress.ip_address(client_ip)
        except:
            raise cherrypy.HTTPError(400, "Unable to determine client address")

        external_ip = self.determineIp()

        if cherrypy.request.as_text:
            return "external_ip={}\nclient_ip={}".format(external_ip, client_ip)

        if cherrypy.request.as_json:
            return {
                "external_ip": external_ip,
                "client_ip": client_ip
            }

        return {
            "external_ip": external_ip,
            "client_ip": client_ip,
            "app_name": self.name
        }

    def determineIp(self):
        """Invoke the dnsomatic plugin to get the application host's external IP"""
        lookup_response = cherrypy.engine.publish("dnsomatic:query")
        return lookup_response[0]

    def ipFromHeader(self, headers):
        for header in ("X-Real-Ip", "Remote-Addr"):
            if header in headers:
                return cherrypy.request.headers[header]
        return None
