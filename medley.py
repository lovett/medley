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
import util.geo
import base64
from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import HtmlFormatter
from titlecase import titlecase

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
        """ Relay deployment notifications from Azure """
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
        """ The application homepage """
        if cherrypy.request.negotiated == "text/plain":
            return "hello"
        else:
            return {
                "message": "hello"
            }

    @cherrypy.expose
    @cherrypy.tools.negotiable()
    @cherrypy.tools.template(template="ip.html")
    def ip(self, token=None):
        """ A dynamic DNS service. Update a local nameserver based on the
        caller's IP address """
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
            return { "message": "ok" }

    @cherrypy.expose
    @cherrypy.tools.negotiable()
    @cherrypy.tools.template(template="headers.html")
    def headers(self):
        """ Display all the headers that were provided by the client """

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
                "data": headers
            }

    def queryWhois(self, address):
        """ Run a whois query by shelling out. Although there are some
        whois-related Python modules that could otherwise be used,
        none were viable for Python 3.2 """

        cherrypy.lib.caching.MemoryCache

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

        print(out_filtered)

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
    def whois(self, address=None):
        """ Display whois and geoip data for an IP address """

        if address is None and cherrypy.request.negotiated == "application/json":
            raise cherrypy.HTTPError(400, "Address not specified")

        data = {
            "address": address
        }

        # geoip lookup
        try:
            geo_db = cherrypy.config.get("geoip.city.filename")
            reader = pygeoip.GeoIP(geo_db)
            data["geo"] = reader.record_by_addr(address)
        except:
            data["geo"] = None

        # whois lookup
        if address:
            data["whois"] = self.queryWhois(address)

        # google charts parameters
        if data["geo"]:
            data["map_region"] = data["geo"]["country_code"]
            if data["map_region"] == "US":
                data["map_region"] += "-" + data["geo"]["region_code"]


        if cherrypy.request.negotiated == "text/plain":
            if "city" in data["geo"] and "country_name" in data["geo"]:
                return "{}, {}".format(data["city"], data["country_name"])
            elif "country_name" in data["geo"]:
                return data["country_name"]
            else:
                return "Unknown"
        else:
            return data

    @cherrypy.expose
    @cherrypy.tools.encode()
    def geoupdate(self):
        """ Download the current version of the GeoLite Legacy City database
        from maxmind.com """

        url = cherrypy.config.get("geoip.city.url")
        destination = cherrypy.config.get("geoip.city.filename")

        gz_file = "{}/{}".format(os.path.dirname(destination),
                                 os.path.basename(url))

        urllib.request.urlcleanup()
        urllib.request.urlretrieve(url, gz_file)
        subprocess.check_call(["gunzip", "-f", gz_file])
        return "ok"

    @cherrypy.expose
    @cherrypy.tools.negotiable()
    @cherrypy.tools.template(template="phone.html")
    def phone(self, number=None):
        """ Given a US phone number, return the state its area code belongs to
        and a description of the area it covers. """

        data = {}

        if number is None and cherrypy.request.negotiated != "text/html":
            raise cherrypy.HTTPError(400, "Address not specified")

        if number is None:
            return data

        number = re.sub(r"\D", "", number)
        number = number.lstrip("1")

        area_code = number[:3]
        number_formatted = re.sub(r"(\d\d\d)(\d\d\d)(\d\d\d\d)", r"(\1) \2-\3", number)

        if len(area_code) is not 3:
            raise cherrypy.HTTPError(400, "Invalid number")

        sparql = """
        PREFIX dbprop: <http://dbpedia.org/property/>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX dbo: <http://dbpedia.org/ontology/>

        SELECT ?state, ?comment, ?redirect WHERE {{
          {{
            ?label rdfs:label "Area code {0}"@en ;
            rdfs:comment ?comment; dbprop:state ?state
            filter (isLiteral(?comment) && langMatches(lang(?comment), "en"))
            filter (isLiteral(?state) && langMatches(lang(?state), "en"))
            .
          }}
          UNION
          {{
            ?label rdfs:label "Area code {0}"@en ;
            dbo:wikiPageRedirects ?redirect .
          }}
        }}
        """.format(area_code)

        params = {
            "query": sparql,
            "format": "json",
            "timeout": "1000"
        }

        sparql_query = "http://dbpedia.org/sparql?"
        sparql_query += urllib.parse.urlencode(params)

        try:
            with urllib.request.urlopen(sparql_query, timeout=7) as request:
                sparql_result = json.loads(request.read().decode("utf-8"))
        except:
            raise cherrypy.HTTPError(500, "timeout while querying dbpedia.org")

        first_result = sparql_result["results"]["bindings"][0]

        if "redirect" in first_result:
            sparql = """
            PREFIX dbo: <http://dbpedia.org/ontology/>
            PREFIX dbprop: <http://dbpedia.org/property/>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            SELECT ?state, ?comment {{
              <{0}> rdfs:comment ?comment ; dbprop:state ?state
              filter(isLiteral(?comment) && langMatches(lang(?comment), "en"))
              filter(isLiteral(?state) && langMatches(lang(?state), "en"))
            }}
            """.format(first_result["redirect"].get("value"))

            params["query"] = sparql
            sparql_query = "http://dbpedia.org/sparql?"
            sparql_query += urllib.parse.urlencode(params)

            with urllib.request.urlopen(sparql_query) as request:
                sparql_result = json.loads(request.read().decode("utf-8"))
                first_result = sparql_result["results"]["bindings"][0]

        comment_sentences = first_result["comment"].get("value").split(". ")

        # Filter out noise
        comment_sentences = [x for x in comment_sentences
                             if re.search(" in (red|blue) (is|are)", x) is None
                             and not re.match("The map to the right", x)
                             and not re.match("Error: ", x)]

        state_abbreviation = first_result["state"].get("value")
        state_name = util.geo.AmericanStates.abbrevToName(state_abbreviation)

        if cherrypy.request.negotiated == "text/plain":
            return state_name
        else:
            data["number"] = number
            data["number_formatted"] = number_formatted
            data["state_abbreviation"] = state_abbreviation
            data["state_name"] = state_name
            data["whitepages_url"] = "http://www.whitepages.com/phone/" + number
            data["bing_url"] = "https://www.bing.com/search?q=" + urllib.parse.quote_plus(number_formatted)
            data["comment"] = ". ".join(comment_sentences[:2])
            return data

    @cherrypy.expose
    @cherrypy.tools.negotiable(media="text/html")
    def highlight(self, extension, content):
        """ Apply syntax highlighting to the provided content and then render
        it as HTML """
        if extension == "json":
            content = json.dumps(json.loads(content), sort_keys=True, indent=4)

        lexer = get_lexer_by_name(extension)
        return highlight(content, lexer, HtmlFormatter(full=True))

    @cherrypy.expose
    @cherrypy.tools.negotiable(media="text/plain")
    def lettercase(self, style, value):
        """ Convert a string value to lowercase, uppercase, or titlecase """
        if style == "title":
            return titlecase(value.lower())

        if style == "lower":
            return value.lower()

        if style == "upper":
            return value.upper()


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
