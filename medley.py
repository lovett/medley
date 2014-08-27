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

        headers = {
            "X-Token": cherrypy.config.get("notifier.token")
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
    @cherrypy.tools.template(template="index.html")
    def ip(self, token=""):
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
                return {
                    "message": ip_address
                }

        host = cherrypy.request.app.config["ip_tokens"].get(token)

        if not host:
            raise cherrypy.HTTPError(404, "Unrecognized token")

        dns_command = copy.copy(cherrypy.config.get("ip.dns.command"))
        if dns_command:
            dns_command[dns_command.index("$ip")] = ip_address
            dns_command[dns_command.index("$host")] = host
            subprocess.call(dns_command)

        if cherrypy.request.negotiated == "text/plain":
            return "ok"
        else:
            return {
                "message": "ok"
            }

    @cherrypy.expose
    @cherrypy.tools.negotiable()
    @cherrypy.tools.template(template="2col.html")
    def headers(self):
        """ Display all the headers that were provided by the client """

        if cherrypy.request.negotiated == "application/json":
            return cherrypy.request.headers
        else:
            headers = [(key.decode('utf-8'), value.decode('utf-8'))
                       for key, value in cherrypy.request.headers.output()]

            headers.sort(key=lambda tup: tup[0])

            return {
                "page_title": "Headers",
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

        whois = out.decode("UTF-8").split("\n")

        # remove legal disclaimers and prefatory comments
        whois = [line for line in whois if not line.startswith("#")]
        whois = [line for line in whois if not "copyright terms" in line]

        # whitespace cleanup
        whois = [line.strip() for line in whois if line]

        # separate label and value for non-comment lines
        whois = [[line] if line.startswith("%")
                 else line.split(":", 1)
                 for line in whois]

        # collapse repeated headers and comment lines
        previous = None
        collapsed_whois = []
        for line in whois:
            if line[0] == previous:
                collapsed_whois[-1][-1] += "\n" + line[1]
            else:
                collapsed_whois.append(line)
            previous = line[0]

        whois = collapsed_whois

        return whois



    @cherrypy.expose
    @cherrypy.tools.negotiable()
    @cherrypy.tools.template(template="geoip.html")
    def geoip(self, address=None):

        """ Determine the geographic location of an IP address """

        db_path = cherrypy.config.get("geoip.city.filename")
        reader = pygeoip.GeoIP(db_path)

        if not db_path:
            raise cherrypy.HTTPError(410, "This endpoint is not active")

        if address is None and cherrypy.request.negotiated == "application/json":
            raise cherrypy.HTTPError(400, "Address not specified")

        if address is None:
            data = {}
        else:
            data = reader.record_by_addr(address)

            if data is None:
                raise cherrypy.HTTPError(404, "No geo records available for " + address)

            data["whois"] = self.queryWhois(address)

        if cherrypy.request.negotiated == "text/plain":
            return "{}, {}".format(data["city"], data["country"])
        else:
            data["address"] = address
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
    @cherrypy.tools.encode()
    def phone(self, number):
        """ Given a US phone number, return the state its area code belongs to
        and a description of the area it covers. """

        number = re.sub(r"\D", "", number)
        number = number.lstrip("1")

        area_code = number[:3]

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

        with urllib.request.urlopen(sparql_query) as request:
            sparql_result = json.loads(request.read().decode("utf-8"))

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

        # Filter noise
        comment_sentences = [x for x in comment_sentences
                             if re.search(" in (red|blue) (is|are)", x) is None
                             and not re.match("The map to the right", x)
                             and not re.match("Error: ", x)]

        reverse_lookup_url = "http://www.whitepages.com/phone/"
        reverse_lookup_url += number

        return {
            "state": first_result["state"].get("value"),
            "reverseLookup": reverse_lookup_url,
            "comment": ". ".join(comment_sentences)
        }

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
