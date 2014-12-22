import cherrypy
import time
import os.path
import os
import pwd
import subprocess
import pygeoip
import re
import urllib
import urllib.request
import urllib.parse
import IPy
import json
import plugins.jinja
import base64
import inspect
import util.phone
import util.net
import memcache
import ssl

import tools.negotiable
cherrypy.tools.negotiable = tools.negotiable.Tool()

import tools.jinja
cherrypy.tools.template = tools.jinja.Tool()

import tools.conditional_auth
cherrypy.tools.conditional_auth = tools.conditional_auth.Tool()


def userFacing(f):
    f.userFacing = True
    return f

class MedleyServer(object):
    mc = None
    template_dir = None

    def __init__(self):
        memcache_host = cherrypy.config.get("memcache.host")
        self.mc = memcache.Client([memcache_host], debug=0)

        self.mc_expire = cherrypy.config.get("memcache.expire")

        self.template_dir = cherrypy.config.get("templates.dir")
        plugins.jinja.Plugin(cherrypy.engine, self.template_dir).subscribe()


    @cherrypy.expose
    @cherrypy.tools.encode()
    @cherrypy.tools.json_in()
    def azure(self, event):
        """Relay deployment notifications from Azure"""
        endpoint = cherrypy.config.get("notifier.url")

        if not endpoint:
            raise cherrypy.HTTPError(410, "This endpoint is not active")
        deployment_url = cherrypy.config.get("azure.url.deployments")
        body = cherrypy.request.json

        if not "siteName" in body:
            raise cherrypy.HTTPError(400, "Site name not specified")

        if not "message" in body:
            body["message"] = None
        else:
            body["message"] = body["message"].split("\n")[0]

        if not "status" in body:
            body["status"] = "unknown"

        if not "complete" in body:
            body["complete"] = False

        notification = {
            "group": "azure",
            "url": deployment_url.format(body["siteName"]),
            "body": body["message"],
            "title": "Deployment to {}".format(body["siteName"])
        }

        if body["status"] == "success" and body["complete"] == True:
            notification["title"] += " is complete"
        elif body["status"] == "failed":
            notification["title"] += " has failed"
        else:
            notification["title"] += " is {}".format(body["status"])

        encoded_notification = urllib.parse.urlencode(notification)
        encoded_notification = encoded_notification.encode('utf-8')

        basic_auth = "%s:%s" % (cherrypy.config.get('notifier.user'), cherrypy.config.get('notifier.pass'))
        basic_auth = basic_auth.encode('utf-8')
        headers = {
            "Authorization": "Basic %s" % base64.b64encode(basic_auth).decode("ascii")
        }

        request = urllib.request.Request(endpoint,
                                         data=encoded_notification,
                                         headers=headers)

        response = urllib.request.urlopen(request)
        response.close()
        return "ok"


    @userFacing
    @cherrypy.expose
    @cherrypy.tools.negotiable()
    @cherrypy.tools.template(template="index.html")
    def index(self):
        """The application homepage lists the available endpoints"""

        endpoints = []
        for name, value in inspect.getmembers(self, inspect.ismethod):
            if name == "index":
                continue

            exposed = getattr(value, "exposed", False)
            userFacing = getattr(value, "userFacing", False)

            if exposed and userFacing:
                endpoints.append((name, value.__doc__))

        if cherrypy.request.negotiated == "text/plain":
            output = ""
            for name, description in endpoints:
                output += "/" + name + "\n"
                output += description + "\n\n"
            return output
        else:
            return {
                "page_title": "Medley",
                "endpoints": endpoints,
            }

    @userFacing
    @cherrypy.expose
    @cherrypy.tools.negotiable()
    @cherrypy.tools.template(template="generic.html")
    def external_ip(self, silent=False):
        """Determine the local machine's external IP"""

        host = cherrypy.request.app.config["ip_tokens"].get("external")
        if not host:
            raise cherrypy.HTTPError(500, "External IP hostname not defined")

        dns_command = cherrypy.config.get("ip.dns.command")[:]

        key = "external_ip"
        cached_value = self.mc.get(key)

        if cached_value:
            ip = cached_value
        else:
            try:
                ip = util.net.externalIp()
                # cache for 10 minutes
                self.mc.set(key, ip, 600)
            except:
                ip = None

        if ip is not None:
            if dns_command:
                dns_command[dns_command.index("$ip")] = ip
                dns_command[dns_command.index("$host")] = host
                subprocess.call(dns_command)
        else:
            ip = "not available"


        if silent:
            cherrypy.response.status = 204
            return
        elif cherrypy.request.negotiated == "text/plain":
            return ip
        elif cherrypy.request.negotiated == "application/json":
            return { "ip": ip }
        else:
            return {
                "page_title": "External IP",
                "message": ip
            }

    @userFacing
    @cherrypy.expose
    @cherrypy.tools.negotiable()
    @cherrypy.tools.template(template="mismatch.html")
    def dnsmatch(self, token=None, email=None, silent=False):
        """Determine whether two or more hosts resolve to the same address"""

        data = {}

        if not token:
            raise cherrypy.HTTPError(400, "No token provided")

        commands = cherrypy.request.app.config["dns_hosts"].get(token)

        if not commands:
            raise cherrypy.HTTPError(400, "Invalid token")

        def runCommand(command):
            process = subprocess.Popen(command, stdout=subprocess.PIPE)
            out, err = process.communicate()
            return (out.strip().decode("utf-8"), err)

        command_results = [runCommand(command) for command in commands]

        data["commands"] = commands
        data["command_results"] = command_results

        if len(set(command_results)) == 1:
            data["result"] = "ok"
        else:
            data["result"] = "mismatch"

        # Email delivery is only triggered from POST requests
        if cherrypy.request.method != "POST":
            email = None

        # Email delivery only occurs when there is a mismatch
        if email and data["result"] == "mismatch":
            config = {
                "template_dir": self.template_dir,
                "template": "dnsmatch.email",
                "subject": "DNS mismatch",
                "smtp": cherrypy.request.app.config["smtp"]
            }
            util.net.sendMessage(config, data)

        if silent:
            cherrypy.response.status = 204
            return
        elif cherrypy.request.negotiated == "text/html":
            data["page_title"] = "DNS Match"
            return data
        elif cherrypy.request.negotiated == "application/json":
            return data
        else:
            return data["result"]


    @userFacing
    @cherrypy.expose
    @cherrypy.tools.negotiable()
    @cherrypy.tools.template(template="ip.html")
    def ip(self, token=None):
        """A combination dynamic DNS and what-is-my-ip service.  If a token is
        provided, updates the local nameserver with the caller's
        address. If no token, returns the caller's address"""

        ip_address = None
        for header in ("X-Real-Ip", "Remote-Addr"):
            try:
                ip_address = cherrypy.request.headers[header]
                break
            except KeyError:
                pass

        if not ip_address:
            raise cherrypy.HTTPError(400, "Unable to determine IP")

        if not token:
            if cherrypy.request.negotiated == "text/plain":
                return ip_address
            else:
                return {"address": ip_address}

        host = cherrypy.request.app.config["ip_tokens"].get(token)
        if not host:
            raise cherrypy.HTTPError(400, "Invalid token")

        dns_command = cherrypy.config.get("ip.dns.command")[:]
        if dns_command:
            dns_command[dns_command.index("$ip")] = ip_address
            dns_command[dns_command.index("$host")] = host
            subprocess.call(dns_command)

        if cherrypy.request.negotiated == "text/plain":
            return "ok"
        else:
            return { "result": "ok" }

    @userFacing
    @cherrypy.expose
    @cherrypy.tools.negotiable()
    @cherrypy.tools.template(template="headers.html")
    def headers(self):
        """Display the incoming request's headers"""

        if cherrypy.request.negotiated == "application/json":
            return cherrypy.request.headers

        headers = [(key.decode('utf-8'), value.decode('utf-8'))
                   for key, value in cherrypy.request.headers.output()]
        headers.sort(key=lambda tup: tup[0])

        if cherrypy.request.negotiated == "text/plain":
            headers = ["{}: {}".format(key, value) for key, value in headers]
            return "\n".join(headers)
        else:
            return {
                "headers": headers
            }

    @userFacing
    @cherrypy.expose
    @cherrypy.tools.negotiable()
    @cherrypy.tools.template(template="whois.html")
    def whois(self, address=None):
        """Display whois and geoip data for an IP address or hostname"""

        if address is None:
            if cherrypy.request.negotiated == "application/json":
                cherrypy.response.status = 400
                return {
                    "message": "Address not specfified"
                }
            if cherrypy.request.negotiated == "text/plain":
                raise cherrypy.HTTPError(400, "Address not specified")
            else:
                return {}

        # Isolate a hostname or IP address
        ip = None
        address_unquoted = urllib.parse.unquote_plus(address).lower()
        address_clean = re.sub(r"[^\w.-\/:?]", "", address_unquoted)

        try:
            IPy.IP(address_clean)
            ip = address_clean
        except ValueError:
            address_parsed = urllib.parse.urlparse(address_clean)
            if address_parsed.hostname:
                address_clean = address_parsed.hostname

        if ip is None:
            ip = util.net.resolveHost(address_clean)

        data = {
            "geo": None,
            "address": address_clean,
            "ip": ip,
            "reverse_host": util.net.reverseLookup(ip)
        }

        # Geoip
        db_path = cherrypy.config.get("database.directory")
        db_path += "/" + os.path.basename(cherrypy.config.get("geoip.download.url"))
        if db_path.endswith(".gz"):
            db_path = db_path[0:-3]

        try:
            reader = pygeoip.GeoIP(db_path)
            data["geo"] = reader.record_by_addr(data["ip"])
        except:
            data["geo"] = None

        key = "whois:{}".format(data["address"])
        cached_value = self.mc.get(key)

        # Whois
        if cached_value:
            data["whois"] = cached_value
        else:
            try:
                data["whois"] = util.net.whois(data["address"])
                self.mc.set(key, data["whois"], self.mc_expire)
            except AssertionError:
                data["whois"] = None

        # Google charts
        try:
            data["map_region"] = data["geo"]["country_code"]
            if data["map_region"] == "US" and data["geo"]["region_code"]:
                data["map_region"] += "-" + data["geo"]["region_code"]
        except:
            data["map_region"] = None


        if cherrypy.request.negotiated == "text/plain":
            if "city" in data["geo"] and "country_name" in data["geo"]:
                return "{}, {}".format(data["geo"]["city"], data["geo"]["country_name"])
            elif "country_name" in data["geo"]:
                return data["geo"]["country_name"]
            else:
                return "Unknown"
        else:
            return data

    @userFacing
    @cherrypy.expose
    @cherrypy.tools.negotiable()
    @cherrypy.tools.template(template="generic.html")
    def geodb(self, action=None):
        """Download the latest GeoLite Legacy City database from maxmind.com"""

        url = cherrypy.config.get("geoip.download.url")
        directory = cherrypy.config.get("database.directory")

        if not (url and directory):
            raise cherrypy.HTTPError(410, "This endpoint is not active")

        download_path = "{}/{}".format(directory.rstrip("/"),
                                 os.path.basename(url))


        try:
            message = "The database was last downloaded on {}".format(time.ctime(os.path.getmtime(download_path[:-3])))
        except OSError:
            message = "The database has not yet been downloaded."

        if action == "update":
            urllib.request.urlcleanup()
            urllib.request.urlretrieve(url, download_path)

            # attempt to gunzip
            if download_path.endswith(".gz"):
                try:
                    subprocess.check_call(["gunzip", "-f", download_path])
                except subprocess.CalledProcessError:
                    os.unlink(download_path)
                    raise cherrypy.HTTPError(500, "Database downloaded but gunzip failed")

            # return a 204 if gunzip was skipped or if it was successful
            cherrypy.response.status = 204
            return

        return {
            "page_title": "Geoupdate",
            "message": message,
            "home_link": True
        }

    @userFacing
    @cherrypy.expose
    @cherrypy.tools.negotiable()
    @cherrypy.tools.template(template="phone.html")
    def phone(self, number=None):
        """Given a US phone number, return the state its area code belongs to
        and a description of the area it covers as well as a recent call history"""

        data = {}

        if number is None:
            message = "Phone number not specified"
            if cherrypy.request.negotiated == "application/json":
                cherrypy.response.status = 400
                return {
                    "message": message
                }
            elif cherrypy.request.negotiated == "text/plain":
                raise cherrypy.HTTPError(400, message)
            else:
                return data

        number = util.phone.sanitize(number)
        area_code = number[:3]

        if len(area_code) is not 3:
            if cherrypy.request.negotiated == "application/json":
                cherrypy.response.status = 400
                return {
                    "message": "Invalid number"
                }
            else:
                raise cherrypy.HTTPError(400, "Invalid number")

        key = "phone:{}".format(area_code)
        cached_value = self.mc.get(key)

        if cached_value:
            location = cached_value
        else:
            try:
                location = util.phone.findAreaCode(area_code)
                self.mc.set(key, location, self.mc_expire)
            except (AssertionError, util.phone.PhoneException):
                location = {}

        history = util.phone.callHistory(cherrypy.config.get("asterisk.cdr_db"), number, 5)

        if cherrypy.request.negotiated == "text/plain":
            return location.get("state_name")
        else:
            data["history"] = history[0]
            data["number"] = number
            data["number_formatted"] = util.phone.format(number)
            data["state_abbreviation"] = location.get("state_abbreviation")
            data["state_name"] = location.get("state_name")
            data["whitepages_url"] = "http://www.whitepages.com/phone/" + number
            data["bing_url"] = "https://www.bing.com/search?q=" + urllib.parse.quote_plus(data["number_formatted"])
            data["comment"] = location.get("comment")
            data["sparql"] = location.get("sparql", [])

            return data

    @userFacing
    @cherrypy.expose
    @cherrypy.tools.negotiable()
    @cherrypy.tools.template(template="lettercase.html")
    def lettercase(self, style=None, value=""):
        """Convert a string value to lowercase, uppercase, or titlecase"""

        result = ""
        if style and value:
            if style == "title":
                result = value.title()
            elif style == "lower":
                result = value.lower()
            elif style == "upper":
                result = value.upper()

        if cherrypy.request.negotiated == "text/plain":
            return result
        elif cherrypy.request.negotiated == "application/json":
            return {
                "result": result
            }
        else:
            return {
                "value": value,
                "result": result,
                "styles": ("title", "lower", "upper"),
                "style": style or "title"
            }



if __name__ == "__main__":
    APP_ROOT = os.path.dirname(os.path.abspath(__file__))
    APP_CONFIG = os.path.join(APP_ROOT, "medley.conf")
    cherrypy.config.update(APP_CONFIG)

    # This should force SSL connections to use TLS and not SSLv3, but
    # appears to have no effect. Do not know why.
    #if (cherrypy.config.get("server.ssl_certificate")):
    #    context = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
    #    cherrypy.config.update({
    #        "server.ssl_context": context
    #    })

    # attempt to drop privileges if daemonized
    USER = cherrypy.config.get("server.user")

    if USER:
        try:
            ACCOUNT = pwd.getpwnam(USER)
            PLUGIN = cherrypy.process.plugins.DropPrivileges(cherrypy.engine,
                                                             umask=0o022,
                                                             uid=ACCOUNT.pw_uid,
                                                             gid=ACCOUNT.pw_gid)
            PLUGIN.subscribe()
        except KeyError:
            MESSAGE = "Unknown user '{}'. Not dropping privileges.".format(USER)
            cherrypy.log.error(MESSAGE, "APP")

    DAEMONIZE = cherrypy.config.get("server.daemonize")
    if DAEMONIZE:
        cherrypy.config.update({'log.screen': False})
        cherrypy.process.plugins.Daemonizer(cherrypy.engine).subscribe()

    PID_FILE = cherrypy.config.get("server.pid")
    if PID_FILE:
        cherrypy.process.plugins.PIDFile(cherrypy.engine, PID_FILE).subscribe()

    cherrypy.quickstart(MedleyServer(), script_name="", config=APP_CONFIG)
