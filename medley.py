import cherrypy
import os.path
import os
import pwd
import subprocess
import geoip2.database
import csv
import re
import urllib
import urllib.parse
import json

class MedleyServer(object):
    @cherrypy.expose
    def index(self):
        return "hello"

    @cherrypy.expose
    @cherrypy.tools.json_out()
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

        dnsCommand = cherrypy.request.app.config["ip_dns"].get("command")
        if dnsCommand:
            dnsCommand[dnsCommand.index("$ip")] = ip
            dnsCommand[dnsCommand.index("$host")] = host
            subprocess.call(dnsCommand);

        return "ok"

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def headers(self):
        return cherrypy.request.headers

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def geoip(self, address):
        dbPath = cherrypy.request.app.config["geo"].get("ip.city")

        reader = geoip2.database.Reader(dbPath)
        response = reader.city(address)
        reader.close()

        return {
            "country": response.country.name,
            "city": response.city.name,
            "timezone": response.location.time_zone,
            "latlong": [response.location.latitude, response.location.longitude]
        }

    @cherrypy.expose
    @cherrypy.tools.json_out()
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
