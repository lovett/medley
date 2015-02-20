import cherrypy
import time
import os.path
import os
import pwd
import subprocess
import re
import urllib.parse
import IPy
import json
import plugins.jinja
import inspect
import util.phone
import util.net
import util.fs
import util.db
import util.decorator
import dogpile.cache
import pytz
from collections import OrderedDict
from datetime import datetime, timedelta

import tools.negotiable
cherrypy.tools.negotiable = tools.negotiable.Tool()

import tools.response_time
cherrypy.tools.response_time = tools.response_time.Tool()

import tools.jinja
cherrypy.tools.template = tools.jinja.Tool()

import tools.conditional_auth
cherrypy.tools.conditional_auth = tools.conditional_auth.Tool()

import tools.capture
cherrypy.tools.capture = tools.capture.Tool()

class MedleyServer(object):
    mc = None
    geoip = None
    cache = dogpile.cache.make_region()

    def __init__(self):
        plugins.jinja.Plugin(cherrypy.engine).subscribe()

        db_dir = os.path.realpath(cherrypy.config.get("database.directory"))

        util.db.setup(db_dir)
        util.db.geoSetup(db_dir, cherrypy.config.get("geoip.download.url"))

        self.cache.configure_from_config(cherrypy.config, "cache.")

    @util.decorator.hideFromHomepage
    @cherrypy.expose
    @cherrypy.tools.encode()
    @cherrypy.tools.json_in()
    @cherrypy.tools.capture()
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


    @util.decorator.hideFromHomepage
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
            hidden = getattr(value, "hide_from_homepage", False)

            if exposed and not hidden:
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

    @util.decorator.hideFromHomepage
    @cherrypy.expose
    @cherrypy.tools.negotiable()
    def external_ip(self):
        """Determine the local machine's external IP"""

        external_hostname = cherrypy.request.app.config["ip_tokens"].get("external")

        if not external_hostname:
            raise cherrypy.HTTPError(500, "External IP hostname not configured")

        dns_command = cherrypy.config.get("ip.dns.command")[:]

        try:
            ip = util.net.externalIp()
        except util.net.NetException as e:
            raise cherrypy.HTTPError(500, str(e))

        if ip and dns_command:
            dns_command[dns_command.index("$ip")] = ip
            dns_command[dns_command.index("$host")] = external_hostname
            subprocess.call(dns_command)

        cherrypy.response.status = 204
        return

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
                "template_dir": cherrypy.config.get("template_dir"),
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
        def whois_query():
            try:
                return util.net.whois(data["address"])
            except AssertionError:
                return None

        key = "whois:{}".format(data["address"])

        data["whois"] = self.cache.get_or_create(
            key, whois_query,
            should_cache_fn= lambda v: v is not None
        )

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

    @cherrypy.expose
    @cherrypy.tools.negotiable()
    @cherrypy.tools.template(template="geodb.html")
    def geodb(self, action=None):
        """Download the latest GeoLite Legacy City database from maxmind.com"""

        url = cherrypy.config.get("geoip.download.url")
        directory = cherrypy.config.get("database.directory")

        if not (url and directory):
            raise cherrypy.HTTPError(410, "This endpoint is not active")

        download_path = "{}/{}".format(directory.rstrip("/"),
                                       os.path.basename(url))

        try:
            modified = os.path.getmtime(download_path.rstrip(".gz"))
            downloaded = datetime.fromtimestamp(modified)
            allow_update = time.time() - modified > 86400
        except OSError:
            downloaded = None
            allow_update = True

        if cherrypy.request.method == "POST" and action == "update":
            try:
                util.net.saveUrl(url, download_path)
            except util.net.NetException as e:
                raise cherrypy.HTTPError(500, str(e))

            # attempt to gunzip
            if download_path.endswith(".gz"):
                try:
                    subprocess.check_call(["gunzip", "-f", download_path])
                    cherrypy.response.status = 204

                    # Re-run setup to ensure the newly downloaded file gets used
                    util.db.geoSetup(directory, url)
                    return
                except subprocess.CalledProcessError:
                    os.unlink(download_path)
                    raise cherrypy.HTTPError(500, "Database downloaded but gunzip failed")


        return {
            "allow_update": allow_update,
            "downloaded": downloaded
        }

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

        def phone_query():
            try:
                return util.phone.findAreaCode(area_code)
            except (AssertionError, util.phone.PhoneException):
                return {}

        key = "phone:{}".format(area_code)
        location = self.cache.get_or_create(
            key, phone_query,
            should_cache_fn= lambda v: v is not None
        )

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


    @cherrypy.expose
    @cherrypy.tools.negotiable()
    @cherrypy.tools.template(template="archive.html")
    def archive(self, date=None, q=None):
        """View and search saved bookmarks"""

        entries = OrderedDict()
        timezone = pytz.timezone(cherrypy.config.get("timezone"))

        if not q:
            bookmarks = util.db.getRecentBookmarks(limit=50)
        else:
            bookmarks = util.db.searchBookmarks(q)

        for bookmark in bookmarks:
            key = bookmark["created"].astimezone(timezone)
            key = key.strftime("%Y-%m-%d")

            if not key in entries:
                entries[key] = []

            entries[key].append(bookmark)

        return {
            "entries": entries
        }

    @cherrypy.expose
    @cherrypy.tools.negotiable()
    @cherrypy.tools.template(template="later.html")
    def later(self, action="edit", title=None, url=None, tags=None, comments=None):
        """Capture a webpage for future reference"""

        error = None

        if action == "edit" and url:
            bookmark = util.db.getBookmarkByUrl(url)

            if bookmark:
                error = "This URL has already been bookmarked"
                title = bookmark["title"]
                url = bookmark["url"]
                tags = bookmark["tags"]
                comments = bookmark["comments"]

            if not title:
                try:
                    html = self.cache.get_or_create(
                        "html:" + url,
                        lambda: util.net.getUrl(url),
                        should_cache_fn = lambda v: v is not None
                    )
                except util.net.NetException as e:
                    error = str(e)
                    html = None

                title = util.net.getHtmlTitle(html)
                title = util.net.reduceHtmlTitle(title)

        if cherrypy.request.method == "POST":
            if not url:
                error = "Address missing"
            else:
                url_id = util.db.saveBookmark(url, title, comments, tags)

                html = self.cache.get("html:" + url)
                if not html:
                    html = util.net.getUrl(url)
                text = util.net.htmlToText(html)
                util.db.saveBookmarkFulltext(url_id, text)
                return "ok".encode("utf-8")

        return {
            "error": error,
            "title": title,
            "url": url,
            "tags": tags,
            "comments": comments
        }



    @util.decorator.hideFromHomepage
    @cherrypy.expose
    @cherrypy.tools.negotiable()
    def annotation(self, annotation_id):
        if cherrypy.request.method == "DELETE":
            if util.db.deleteAnnotation(annotation_id) == 1:
                return "ok".encode("utf-8")

        raise cherrypy.HTTPError(400)

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

    @cherrypy.expose
    @cherrypy.tools.negotiable()
    @cherrypy.tools.template(template="captures.html")
    def captures(self, q=None):
        """Display captured requests"""

        return {
            "q": q,
            "captures": util.db.getCaptures(q)
        }


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
    app_root = os.path.dirname(os.path.abspath(__file__))

    # The default configuration comes from /etc/medley.conf or
    # default.conf in the current directory. This makes running
    # out of the box easy, and starting from a blank slate possible.
    default_config = "/etc/medley.conf"
    if not os.path.isfile(default_config):
        default_config = os.path.join(app_root, "default.conf")

    # The configuration is applied twice, because a single file is
    # used for both global and application entries
    cherrypy.config.update(default_config)
    app = cherrypy.tree.mount(MedleyServer(), config=default_config)

    # The default configuration can be selectively overriden, which is
    # useful during development.
    local_config = os.path.join(app_root, "local.conf")
    try:
        cherrypy.config.update(local_config)
        app.merge(local_config)
    except:
        pass

    # Attempt to drop privileges if daemonized
    if cherrypy.config.get("server.daemonize"):

        cherrypy.process.plugins.Daemonizer(cherrypy.engine).subscribe()

        pid_file = cherrypy.config.get("server.pid")
        if pid_file:
            cherrypy.process.plugins.PIDFile(cherrypy.engine, pid_file).subscribe()

    cherrypy.engine.start()
    cherrypy.engine.block()
