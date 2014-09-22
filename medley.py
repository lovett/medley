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
from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import HtmlFormatter

import tools.negotiable
cherrypy.tools.negotiable = tools.negotiable.Tool()

import tools.jinja
cherrypy.tools.template = tools.jinja.Tool()

class MedleyServer(object):

    def __init__(self):
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

    def queryWhois(self, address):
        """Run a whois query by shelling out. Although there are some
        whois-related Python modules that could otherwise be used,
        none were viable for Python 3.2"""

        process = subprocess.Popen(["whois", address],
                                   stdout=subprocess.PIPE)
        out, err = process.communicate()

        if err:
            raise cherrypy.HTTPError(500, err)

        try:
            out_raw = out.decode("utf-8")
        except UnicodeDecodeError:
            out_raw = out.decode("iso-8859-1")

        out_raw = out_raw.split("\n")

        out_filtered = []
        for line in out_raw:
            line = line.strip()

            # remove comments
            if line.startswith(("#", "%")):
                continue

            # separate label and value for non-comment lines
            line = re.sub(r"\s+", " ", line)
            fields = line.split(": ", 1)

            # skip lines with no value
            if len(fields) == 1:
                continue

            fields[0] = re.sub(r"([a-z])([A-Z][a-z])", r"\1 \2", fields[0]).title()


            out_filtered.append(fields)

        # collapse repeated headers and comment lines
        previous = None
        out_collapsed = []
        for line in out_filtered:
            if line[0] == previous:
                out_collapsed[-1][-1] += "\n" + line[1]
            else:
                out_collapsed.append(line)
            previous = line[0]

        return out_collapsed



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

        data["whois"] = self.queryWhois(ip)

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
            "message": "ok"
        }

    @cherrypy.expose
    @cherrypy.tools.negotiable()
    @cherrypy.tools.template(template="phone.html")
    def phone(self, number=None):
        """Given a US phone number, return the state its area code belongs to
        and a description of the area it covers"""

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

        area_code_query = """
        PREFIX dbp: <http://dbpedia.org/property/>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT ?state_abbrev, ?comment WHERE {{
            ?s dbp:this ?o .
            ?s dbp:state ?state_abbrev .
            ?s rdfs:comment ?comment
            FILTER (regex(?o, "{0}", "i"))
            FILTER (langMatches(lang(?state_abbrev), "en"))
        }} LIMIT 1
        """.format(area_code)

        params = {
            "query": area_code_query,
            "format": "json",
            "timeout": "1000"
        }

        query = "http://dbpedia.org/sparql?"
        query += urllib.parse.urlencode(params)

        try:
            with urllib.request.urlopen(query, timeout=7) as request:
                result = json.loads(request.read().decode("utf-8"))
            first_result = result["results"]["bindings"][0]
            state_abbrev = first_result["state_abbrev"].get("value")
            isocode = "US-" + state_abbrev
            comment = first_result["comment"].get("value").split(". ")
        except:
            state_abbrev = None
            isocode = None
            comment = []
            state_name = None
            comment = "The location of this number could not be found."

        # Take the first two sentences from the comment
        comment = [sentence for sentence in comment
                   if re.search(" in (red|blue) (is|are)", sentence) is None
                   and not re.match("The map to the right", sentence)
                   and not re.match("Error: ", sentence)][:2]
        comment = ". ".join(comment)
        if not comment.endswith("."):
            comment += "."

        if isocode:
            state_name_query = """
            PREFIX dbp: <http://dbpedia.org/property/>
            SELECT ?name WHERE {{
                 ?s dbp:isocode "{0}"@en .
                 ?s dbp:name ?name .
            }} LIMIT 1
            """.format(isocode)

            params["query"] = state_name_query
            query = "http://dbpedia.org/sparql?"
            query += urllib.parse.urlencode(params)

            try:
                with urllib.request.urlopen(query, timeout=7) as request:
                    result = json.loads(request.read().decode("utf-8"))
                first_result = result["results"]["bindings"][0]
                state_name = first_result["name"].get("value")
            except:
                state_name = "Unknown"

        if cherrypy.request.negotiated == "text/plain":
            return state_name or "Unknown"
        else:
            data["number"] = number
            data["number_formatted"] = util.phone.format(number)
            data["state_abbreviation"] = state_abbrev
            data["state_name"] = state_name
            data["whitepages_url"] = "http://www.whitepages.com/phone/" + number
            data["bing_url"] = "https://www.bing.com/search?q=" + urllib.parse.quote_plus(data["number_formatted"])
            data["comment"] = comment
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
