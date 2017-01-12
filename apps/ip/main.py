import subprocess
import cherrypy
import tools.negotiable
import tools.jinja
import util.net
import util.cache
import apps.registry.models
import ipaddress

class Controller:
    """Show the address of the client and the server"""

    name = "IP"

    exposed = True

    user_facing = True


    def validateIp(self, value):
        try:
            ipaddress.ip_address(value)
            return True
        except:
            return False

    def ipFromHeader(self, headers):
        for header in ("X-Real-Ip", "Remote-Addr"):
            if header in headers:
                return cherrypy.request.headers[header]
        return None

    def announceValueChange(self, old_ip, new_ip, host):
        notifier = cherrypy.config.get("notifier")
        notification = {
            "group": "sysdown",
            "title": "IP address of {} has changed".format(host),
            "body": "New address is {}. Old address was {}".format(new_ip, old_ip)
        }
        util.net.sendNotification(notification, notifier)

    def PUT(self, token=None):
        cache = util.cache.Cache()
        registry = apps.registry.models.Registry()

        dns_command = registry.search(key="ip:dns_command")
        if not dns_command:
            cherrypy.response.status = 409
            return

        dns_command = dns_command[0]["value"].split(" ")

        token_from_registry = registry.search(key="ip:token:{}".format(token))
        if not token_from_registry:
            cherrypy.response.status = 409
            return

        host = token_from_registry[0]["value"]

        cache_key = "ip:{}".format(host)
        cached_value = cache.get(cache_key)

        if token == "external":
            ip_address = util.net.externalIp()
        else:
            ip_address = self.ipFromHeader(cherrypy.request.headers)

        if ip_address != cached_value[0]:
            cache.set(cache_key, ip_address, 86400)
            dns_command[dns_command.index("$ip")] = ip_address
            dns_command[dns_command.index("$host")] = host
            subprocess.call(dns_command)
            self.announceValueChange(cached_value, ip_address, host)
            cherrypy.response.status = 201
        else:
            cherrypy.response.status = 304


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
                "external_ip": external_ip,
                "app_name": self.name
            }
