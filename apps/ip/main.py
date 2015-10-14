import subprocess
import cherrypy
import tools.negotiable
import tools.jinja
import util.net
import util.cache
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

        try:
            dns_command = cherrypy.config.get("ip.dns.command")[:]
        except TypeError:
            cherrypy.response.status = 409
            return

        host = cherrypy.config["ip.tokens"].get(token)
        if not host:
            raise cherrypy.HTTPError(400, "Invalid token")

        cache_key = "ip:{}".format(host)
        cached_value = cache.get(cache_key)

        if token == "external":
            ip_address = util.net.externalIp()
        else:
            ip_address = self.ipFromHeader(cherrypy.request.headers)

        if ip_address != cached_value:
            cache.set(cache_key, ip_address, 86400)
            dns_command[dns_command.index("$ip")] = ip_address
            dns_command[dns_command.index("$host")] = host
            subprocess.call(dns_command)
            self.announceValueChange(cached_value, ip_address, host)

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
