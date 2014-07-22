import cherrypy
import os.path
import os
import pwd
import subprocess
import pygeoip
import csv
import re
import urllib
import urllib.request
import urllib.parse
import json
import copy
import tempfile
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
        templateDir = cherrypy.config.get("templates.dir")
        plugins.jinja.Plugin(cherrypy.engine, templateDir).subscribe()


    @cherrypy.expose
    @cherrypy.tools.encode()
    @cherrypy.tools.json_in()
    def azure(self, event):

        endpoint = cherrypy.config.get("notifier.url")

        if not endpoint:
            raise cherrypy.HTTPError(410, "This endpoint is not active")

        body = cherrypy.request.json

        notification = {
            "group": "azure",
            "url": cherrypy.config.get("azure.url.deployments").format(body["siteName"]),
            "body": body["message"]
        }

        if body["status"] == "success" and body["complete"] == True:
            notification["title"] = "Deployment to {} is complete".format(body["siteName"])
        else:
            notification["title"] = "Deployment to {} is {}".format(body["siteName"], body["status"])

        encodedNotification = urllib.parse.urlencode(notification).encode('utf-8')

        headers= {
            "X-Token": cherrypy.config.get("notifier.token")
        }



        request = urllib.request.Request(endpoint, data=encodedNotification, headers=headers)

        response = urllib.request.urlopen(request)
        response.close()
        return "ok"


    @cherrypy.expose
    @cherrypy.tools.negotiable()
    @cherrypy.tools.template(template='index.html')
    def index(self):
        if cherrypy.request.negotiated == 'text/plain':
            return 'hello'
        else:
            return {
                'message': 'hello'
            }

    @cherrypy.expose
    @cherrypy.tools.negotiable(media='text/plain')
    def ip(self, token=""):

        ip = None
        for header in ("X-Real-Ip", "Remote-Addr"):
            try:
                ip = cherrypy.request.headers[header]
                break
            except KeyError:
                pass

        if not ip:
            raise cherrypy.HTTPError(400, "Unable to determine IP")

        if not token:
            return ip

        host = cherrypy.request.app.config["ip_tokens"].get(token)

        if not host:
            raise cherrypy.HTTPError(404, "Unrecognized token")

        dnsCommand = copy.copy(cherrypy.config.get("ip.dns.command"))
        if dnsCommand:
            dnsCommand[dnsCommand.index("$ip")] = ip
            dnsCommand[dnsCommand.index("$host")] = host
            subprocess.call(dnsCommand);

        return "ok"

    @cherrypy.expose
    @cherrypy.tools.negotiable()
    @cherrypy.tools.template(template="2col.html")
    def headers(self):
        """ Display all the headers that were provided by the client."""

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

    @cherrypy.expose
    @cherrypy.tools.negotiable()
    @cherrypy.tools.template(template="2col.html")
    def geoip(self, address):
        dbPath = cherrypy.config.get("geoip.city.filename")

        reader = pygeoip.GeoIP(dbPath)
        response = reader.record_by_addr(address)

        whois = subprocess.Popen(["whois", address], stdout=subprocess.PIPE)
        out, err = whois.communicate()
        out = out.decode('UTF-8')
        orgNames = [line for line in out.split("\n") if re.match("OrgName:", line)]
        orgNames = [re.sub("OrgName:\s+", "", line) for line in orgNames]
        if len(orgNames) > 0:
            org = orgNames.pop()
        else:
            org = None

        data =  {
            "country": response["country_name"],
            "country_code": response["country_code"],
            "city": response["city"],
            "region_code": response["region_code"],
            "area_code": response["area_code"],
            "timezone": response["time_zone"],
            "latitude": response["latitude"],
            "longitude": response["longitude"],
            "organization": org
        }

        if cherrypy.request.negotiated == "application/json":
            return data
        if cherrypy.request.negotiated == "text/plain":
            return "{}, {}".format(data["city"], data["country"])
        else:
            return {
                "page_title": "GeoIP",
                "data": data.items()
            }

    @cherrypy.expose
    @cherrypy.tools.encode()
    def geoupdate(self):
        """ Download the current version of the GeoLite Legacy City database from maxmind.com """

        url = cherrypy.config.get("geoip.city.url")
        destination = cherrypy.config.get("geoip.city.filename")

        gzFile = "{}/{}".format(os.path.dirname(destination), os.path.basename(url))

        urllib.request.urlcleanup()
        urllib.request.urlretrieve(url, gzFile)
        subprocess.check_call(["gunzip", "-f", gzFile]);
        return "ok"

    @cherrypy.expose
    @cherrypy.tools.negotiable()
    @cherrypy.tools.encode()
    def phone(self, number):
        """ Given a US phone number, return the state its area code belongs to
        and a description of the area it covers. """

        number = re.sub("\D", "", number)
        number = number.lstrip("1")

        areaCode = number[:3]

        if len(areaCode) is not 3:
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
        """.format(areaCode)

        params = {
            "query": sparql,
            "format": "json",
            "timeout": "1000"
        }

        sparqlQuery = "http://dbpedia.org/sparql?%s" % urllib.parse.urlencode(params)

        with urllib.request.urlopen(sparqlQuery) as request:
            sparqlResult = json.loads(request.read().decode("utf-8"))

        firstResult = sparqlResult["results"]["bindings"][0]

        if "redirect" in firstResult:
            sparql = """
            PREFIX dbo: <http://dbpedia.org/ontology/>
            PREFIX dbprop: <http://dbpedia.org/property/>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            SELECT ?state, ?comment {{
              <{0}> rdfs:comment ?comment ; dbprop:state ?state
              filter(isLiteral(?comment) && langMatches(lang(?comment), "en"))
              filter(isLiteral(?state) && langMatches(lang(?state), "en"))
            }}
            """.format(firstResult["redirect"].get("value"))

            params["query"] = sparql
            sparqlQuery = "http://dbpedia.org/sparql?%s" % urllib.parse.urlencode(params)

            with urllib.request.urlopen(sparqlQuery) as request:
                sparqlResult = json.loads(request.read().decode("utf-8"))
                firstResult = sparqlResult["results"]["bindings"][0]

        commentSentences = firstResult["comment"].get("value").split(". ")

        # Filter noise
        commentSentences = [x for x in commentSentences
                            if re.search(" in (red|blue) (is|are)",x) is None
                            and not re.match("The map to the right", x)
                            and not re.match("Error: ", x)]

        return {
            "state": firstResult["state"].get("value"),
            "reverseLookup": "http://www.whitepages.com/phone/{}".format(number),
            "comment": ". ".join(commentSentences)
        }

    @cherrypy.expose
    @cherrypy.tools.negotiable(media="text/html")
    def highlight(self, extension, content):
        if extension == "json":
            content = json.dumps(json.loads(content), sort_keys=True, indent=4)

        lexer = get_lexer_by_name(extension)
        return highlight(content, lexer, HtmlFormatter(full=True))

    @cherrypy.expose
    @cherrypy.tools.negotiable(media="text/plain")
    def lettercase(self, style, value):
        if style == "title":
            return titlecase(value.lower())

        if style == "lower":
            return value.lower()

        if style == "upper":
            return value.upper()


if __name__ == "__main__":
    appRoot = os.path.dirname(os.path.abspath(__file__))
    appConfig = os.path.join(appRoot, "medley.conf")
    cherrypy.config.update(appConfig)

    # attempt to drop privileges if daemonized
    user = cherrypy.config.get("server.user")
    if user:
        try:
            account = pwd.getpwnam(user)
            cherrypy.process.plugins.DropPrivileges(cherrypy.engine, umask=0o022, uid=account.pw_uid, gid=account.pw_gid).subscribe()
        except KeyError:
            cherrypy.log.error("Unable to look up the user '{}'. Not dropping privileges.".format(user), "APP")
            pass

    daemonize = cherrypy.config.get("server.daemonize")
    if daemonize:
        cherrypy.config.update({'log.screen': False})
        cherrypy.process.plugins.Daemonizer(cherrypy.engine).subscribe()

    pidFile = cherrypy.config.get("server.pid")
    if pidFile:
        cherrypy.process.plugins.PIDFile(cherrypy.engine, pidFile).subscribe()

    cherrypy.quickstart(MedleyServer(), "/", appConfig)
