import cherrypy
import time
import os.path
import os
import pwd
import subprocess
import re
import urllib
import urllib.request
import urllib.parse
import IPy
import json
import plugins.jinja
import plugins.urlfetch
import base64
import inspect
import util.phone
import util.net
import util.fs
import util.cache
import util.db
import util.decorator
import ssl
import string
from collections import defaultdict
from datetime import datetime, timedelta

import tools.negotiable
cherrypy.tools.negotiable = tools.negotiable.Tool()

import tools.jinja
cherrypy.tools.template = tools.jinja.Tool()

import tools.conditional_auth
cherrypy.tools.conditional_auth = tools.conditional_auth.Tool()

class MedleyServer(object):
    mc = None
    template_dir = None
    geoip = None

    def __init__(self):
        self.template_dir = cherrypy.config.get("templates.dir")
        plugins.jinja.Plugin(cherrypy.engine, self.template_dir).subscribe()
        plugins.urlfetch.Plugin(cherrypy.engine).subscribe()

        util.db.setup(cherrypy.config.get("database.directory"))
        util.db.geoSetup(cherrypy.config.get("database.directory"),
                         cherrypy.config.get("geoip.download.url"))


    @cherrypy.expose
    @cherrypy.tools.encode()
    @cherrypy.tools.json_in()
    def azure(self, event):
        """Relay deployment notifications from Azure"""

        notifier = cherrypy.request.app.config["notifier"]

        if not notifier.get("endpoint"):
            raise cherrypy.HTTPError(410, "This endpoint is not active")

        details = cherrypy.request.json

        if not details.get("siteName"):
            raise cherrypy.HTTPError(400, "Site name not specified")

        notification = {
            "group": "azure",
            "url": cherrypy.request.config.get("deployment_url").format(details["siteName"]),
            "body": details.get("message", "").split("\n")[0],
            "title": "Deployment to {}".format(details["siteName"])
        }

        if details.get("status") == "success" and details.get("complete") == True:
            notification["title"] += " is complete"
        elif details.get("status") == "failed":
            notification["title"] += " has failed"
        else:
            notification["title"] += " is {}".format(details.get("status", "not specified"))

        util.net.sendNotification(notification, notifier)
        return "ok"


    @util.decorator.userFacing
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
            util.decorator.userFacing = getattr(value, "userFacing", False)

            if exposed and util.decorator.userFacing:
                endpoints.append((name, value.__doc__))

        if cherrypy.request.negotiated == "text/plain":
            output = ""
            for name, description in endpoints:
                output += "/" + name + "\n"
                output += str(description) + "\n\n"
            return output
        elif cherrypy.request.negotiated == "application/json":
            return endpoints
        else:
            return {
                "page_title": "Medley",
                "endpoints": endpoints
            }

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

        ip = util.cache.get(key)

        if ip is None:
            ip = util.net.externalIp()
            # cache for 10 minutes
            util.cache.set(key, ip, time.time() + 600)

        if ip and dns_command:
            dns_command[dns_command.index("$ip")] = ip
            dns_command[dns_command.index("$host")] = host
            subprocess.call(dns_command)

        if silent:
            cherrypy.response.status = 204
            return
        elif cherrypy.request.negotiated == "text/plain":
            return ip or "not available"
        elif cherrypy.request.negotiated == "application/json":
            return { "ip": ip }
        else:
            return {
                "page_title": "External IP",
                "message": ip
            }

    @util.decorator.userFacing
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


    @util.decorator.userFacing
    @cherrypy.expose
    @cherrypy.tools.negotiable()
    @cherrypy.tools.template(template="ip.html")
    def ip(self, token=None):
        """Display internal and external IP addresses"""

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
            external_ip = util.net.externalIp()
            if cherrypy.request.negotiated == "text/plain":
                return ip_address
            else:
                return {
                    "address": ip_address,
                    "external_ip": external_ip
                }

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

    @util.decorator.userFacing
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

    @util.decorator.userFacing
    @cherrypy.expose
    @cherrypy.tools.negotiable()
    @cherrypy.tools.template(template="whois.html")
    def whois(self, address=None):
        """Display whois and geoip data for an IP address or hostname"""

        if address is None:
            if cherrypy.request.negotiated == "application/json":
                cherrypy.response.status = 400
                return {
                    "message": "Address not specified"
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

        try:
            geo = util.db.geoip(ip)
        except:
            geo = None

        data = {
            "geo": geo,
            "address": address_clean,
            "ip": ip,
            "reverse_host": util.net.reverseLookup(ip)
        }

        # Whois
        key = "whois:{}".format(data["address"])
        cached_value = util.cache.get(key)
        if cached_value:
            data["whois"] = cached_value
        else:
            try:
                data["whois"] = util.net.whois(data["address"])
                util.cache.set(key, data["whois"], time.time() + 600)
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

    @util.decorator.userFacing
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
            "page_title": "Geodb",
            "message": message,
            "home_link": True
        }

    @util.decorator.userFacing
    @cherrypy.expose
    @cherrypy.tools.negotiable()
    @cherrypy.tools.template(template="phone.html")
    def phone(self, number=None):
        """Get the geographic location and recent call history for a phone number"""

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
        location = util.cache.get(key)

        if location is None:
            try:
                location = util.phone.findAreaCode(area_code)
                util.cache.set(key, location, time.time() + 600)
            except (AssertionError, util.phone.PhoneException):
                location = {}

        if cherrypy.request.negotiated == "text/plain":
            return location.get("state_name", "Unknown")
        else:
            history = util.phone.callHistory(cherrypy.config.get("asterisk.cdr_db"), number, 5)
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

    @util.decorator.userFacing
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


    @util.decorator.userFacing
    @cherrypy.expose
    @cherrypy.tools.negotiable()
    @cherrypy.tools.template(template="archive.html")
    def archive(self, date=None, q=None):
        """View and search saved bookmarks"""

        entries = defaultdict(list)

        if not q:
            bookmarks = util.db.getRecentBookmarks(limit=50)
        else:
            bookmarks = util.db.searchBookmarks(q)

        for bookmark in bookmarks:
            key = bookmark["created"].strftime("%Y-%m-%d")
            entries[key].append(bookmark)

        print(entries)
        return {
            "entries": entries
        }

    @util.decorator.userFacing
    @cherrypy.expose
    @cherrypy.tools.negotiable()
    @cherrypy.tools.template(template="later.html")
    def later(self, action="edit", title=None, url=None, tags=None, comments=None):
        """Capture a webpage for future reference"""

        error = None

        if action == "edit" and url:
            bookmark = util.db.getBookmarkByUrl(url)

            if bookmark is not None:
                error = "This URL has already been bookmarked"
                title = bookmark["title"]
                url = bookmark["url"]
                tags = bookmark["tags"]
                comments = bookmark["comments"]

            if not title:
                title = util.net.getHtmlTitleYQL(url)

                if title is None and url.startswith("https:"):
                    title = util.net.getHtmlTitleYQL(url.replace("https:", "http:"))

        if cherrypy.request.method == "POST":
            if not url:
                error = "Address missing"
            else:
                url_id = util.db.saveBookmark(url, title, comments, tags)
                cherrypy.engine.publish("bookmark-fetch", url_id)
                return "ok".encode("utf-8")

        return {
            "error": error,
            "title": title,
            "url": url,
            "tags": tags,
            "comments": comments
        }



    @cherrypy.expose
    @cherrypy.tools.negotiable()
    def annotation(self, annotation_id):
        if cherrypy.request.method == "DELETE":
            if util.db.deleteAnnotation(annotation_id) == 1:
                return "ok".encode("utf-8")

        raise cherrypy.HTTPError(400)

    @util.decorator.userFacing
    @cherrypy.expose
    @cherrypy.tools.negotiable()
    @cherrypy.tools.template(template="annotations.html")
    def annotations(self, key=None, value=None):
        """A general-purpose key-value store"""

        if key and value and cherrypy.request.method == "POST":
            util.db.saveAnnotation(key, value)
            annotations = util.db.getAnnotations(key, limit=1)

            if len(annotations) != 1:
                raise cherrypy.HTTPError(400)

            if cherrypy.request.negotiated == "application/json":

                return {
                    "id": annotations[0]["id"],
                    "key": annotations[0]["key"],
                    "value": annotations[0]["value"],
                    "created": annotations[0]["created"].strftime("%A %b %d, %Y %I:%M %p")
                }

        return {
            "key": key,
            "value": value,
            "annotations": util.db.getAnnotations()
        }


    @util.decorator.userFacing
    @cherrypy.expose
    @cherrypy.tools.negotiable()
    @cherrypy.tools.template(template="visitors.html")
    def visitors(self, q=None):
        """Search website access logs"""

        if not q:
            q = "\n".join(cherrypy.request.config.get("default_query"))
        else:
            q = re.sub("[^\d\w -:;,\n]+", "", q, flags=re.UNICODE)


        q = q.replace("date today", datetime.now().strftime("date %Y-%m-%d"))
        q = q.replace("date yesterday", (datetime.now() - timedelta(days=1)).strftime("date %Y-%m-%d"))

        logdir = cherrypy.request.config.get("logdir")

        results = None

        filters = {
            "include": [],
            "exclude": [],
            "shun": [],
            "date":  []
        }

        for line in q.split("\n"):
            try:
                action, value = line.split(" ", 1)
            except ValueError:
                continue

            if action in filters.keys():
                filters[action].append(value)

        if q:
            results, duration = util.fs.appengine_log_grep(logdir, filters, 100)

        keys = list({"ip:{}".format(result["ip"]) for result in results.matches})


        ip_annotations = util.db.getAnnotations(keys)
        ip_labels = {}
        for annotation in ip_annotations:
            address = annotation["key"][3:]
            ip_labels[address] = annotation["value"]

        query_annotations = util.db.getAnnotationsByPrefix("visitors")

        for result in results.matches:
            geo = util.db.geoip(result["ip"])
            result["geo"] = geo
            result["ip_label"] = ip_labels.get(result["ip"])

        return {
            "q": q,
            "results": results.matches,
            "total_matches": results.count,
            "result_limit": results.limit,
            "duration": duration,
            "site_domains": cherrypy.request.config.get("site_domains"),
            "queries": query_annotations
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
                                                             umask=0o022, # an octal in Python3, not a typo
                                                             uid=ACCOUNT.pw_uid,
                                                             gid=ACCOUNT.pw_gid)
            PLUGIN.subscribe()
        except KeyError:
            MESSAGE = "Unknown user '{}'. Not dropping privileges.".format(USER)
            cherrypy.log.error(MESSAGE, "APP")

    cherrypy.config.update({
        "tools.encode.on": False
    })

    if cherrypy.config.get("server.daemonize"):
        cherrypy.process.plugins.Daemonizer(cherrypy.engine).subscribe()

    PID_FILE = cherrypy.config.get("server.pid")
    if PID_FILE:
        cherrypy.process.plugins.PIDFile(cherrypy.engine, PID_FILE).subscribe()

    cherrypy.quickstart(MedleyServer(), script_name="", config=APP_CONFIG)
