import cherrypy
import os.path
import os
import pwd
import subprocess
import pygeoip
import re
import urllib
import urllib.request
import urllib.parse
import json
import copy
import plugins.jinja
import base64
import inspect
import util.phone
import util.whois
import memcache
from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import HtmlFormatter

import tools.negotiable
cherrypy.tools.negotiable = tools.negotiable.Tool()

import tools.jinja
cherrypy.tools.template = tools.jinja.Tool()



class MedleyServer(object):
    mc = None

    def __init__(self):
        memcache_host = cherrypy.config.get("memcache.host")
        self.mc = memcache.Client([memcache_host], debug=0)

        self.mc_expire = cherrypy.config.get("memcache.expire")

        template_dir = cherrypy.config.get("templates.dir")
        plugins.jinja.Plugin(cherrypy.engine, template_dir).subscribe()


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


    @cherrypy.expose
    @cherrypy.tools.negotiable()
    @cherrypy.tools.template(template="index.html")
    def index(self):
        """The application homepage lists the available endpoints"""

        endpoints = []
        for name, value in inspect.getmembers(self, inspect.ismethod):
            if name == "index":
                continue

            if getattr(value, "exposed", False):
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

        dns_command = copy.copy(cherrypy.config.get("ip.dns.command"))
        if dns_command:
            dns_command[dns_command.index("$ip")] = ip_address
            dns_command[dns_command.index("$host")] = host
            subprocess.call(dns_command)

        if cherrypy.request.negotiated == "text/plain":
            return "ok"
        else:
            return { "result": "ok" }

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

    @cherrypy.expose
    @cherrypy.tools.negotiable()
    @cherrypy.tools.template(template="whois.html")
    def whois(self, ip=None):
        """Display whois and geoip data for an IP"""

        data = {
            "ip": ip,
            "geo": None
        }

        if ip is None:
            if cherrypy.request.negotiated == "application/json":
                cherrypy.response.status = 400
                return {
                    "message": "IP address not specfified"
                }
            if cherrypy.request.negotiated == "text/plain":
                raise cherrypy.HTTPError(400, "Ip not specified")
            else:
                return data

        # whois lookup
        db_path = cherrypy.config.get("database.directory")
        db_path += "/" + os.path.basename(cherrypy.config.get("geoip.download.url"))
        if db_path.endswith(".gz"):
            db_path = db_path[0:-3]

        try:
            reader = pygeoip.GeoIP(db_path)
            data["geo"] = reader.record_by_addr(ip)
        except:
            pass

        key = "whois:{}".format(ip)
        cached_value = self.mc.get(key)

        if cached_value:
            data["whois"] = cached_value
        else:
            data["whois"] = util.whois.query(ip)
            self.mc.set(key, data["whois"], self.mc_expire)

        # google charts parameters
        if data["geo"]:
            data["map_region"] = data["geo"]["country_code"]
            if data["map_region"] == "US":
                data["map_region"] += "-" + data["geo"]["region_code"]


        if cherrypy.request.negotiated == "text/plain":
            if "city" in data["geo"] and "country_name" in data["geo"]:
                return "{}, {}".format(data["geo"]["city"], data["geo"]["country_name"])
            elif "country_name" in data["geo"]:
                return data["geo"]["country_name"]
            else:
                return "Unknown"
        else:
            return data

    @cherrypy.expose
    @cherrypy.tools.negotiable()
    @cherrypy.tools.template(template="generic.html")
    def geoupdate(self):
        """Download the latest GeoLite Legacy City database from maxmind.com"""

        url = cherrypy.config.get("geoip.download.url")
        directory = cherrypy.config.get("database.directory")

        if not (url and directory):
            raise cherrypy.HTTPError(410, "This endpoint is not active")

        download_path = "{}/{}".format(directory.rstrip("/"),
                                 os.path.basename(url))

        urllib.request.urlcleanup()
        urllib.request.urlretrieve(url, download_path)

        if download_path.endswith(".gz"):
            try:
                subprocess.check_call(["gunzip", "-f", download_path])
            except subprocess.CalledProcessError:
                os.unlink(download_path)
                raise cherrypy.HTTPError(500, "Database downloaded but gunzip failed")

        return {
            "page_title": "Geoupdate",
            "message": "ok",
            "home_link": True
        }

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
            location = util.phone.findAreaCode(area_code)
            self.mc.set(key, location, self.mc_expire)

        history_db = "{}/{}".format(cherrypy.config.get("database.directory"),
                                    cherrypy.config.get("asterisk.cdr_db"))
        history = util.phone.callHistory(history_db, number, 5)

        if cherrypy.request.negotiated == "text/plain":
            return location.state_name
        else:
            data["history"] = history[0]
            data["number"] = number
            data["number_formatted"] = util.phone.format(number)
            data["state_abbreviation"] = location.state_abbreviation
            data["state_name"] = location.state_name
            data["whitepages_url"] = "http://www.whitepages.com/phone/" + number
            data["bing_url"] = "https://www.bing.com/search?q=" + urllib.parse.quote_plus(data["number_formatted"])
            data["comment"] = location.comment
            return data

    @cherrypy.expose
    @cherrypy.tools.negotiable(media="text/html")
    def highlight(self, extension, content):
        """Syntax highlight the given input and render as HTML"""
        if extension == "json":
            content = json.dumps(json.loads(content), sort_keys=True, indent=4)

        lexer = get_lexer_by_name(extension)
        return highlight(content, lexer, HtmlFormatter(full=True))

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
