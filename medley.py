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
        """
        Given a US phone number, return the corresponding state its area code belongs to.
        """
        number = re.sub("\D", "", number)
        number = number.lstrip("1")

        areaCode = number[:3]

        params = {
            "default-graph-uri": "http://dbpedia.org",
            "query": "select * where { dbpedia:Area_code_%s geo:lat ?lat; geo:long ?long }" % (areaCode),
            "format": "json",
            "timeout": "1000"
        }

        sparqlQuery = "http://dbpedia.org/sparql?%s" % urllib.parse.urlencode(params)

        with urllib.request.urlopen(sparqlQuery) as request:
            sparqlResult = json.loads(request.read().decode("utf-8"))

        firstResult = sparqlResult["results"]["bindings"][0]

        params = {
            "latlng": "%s,%s" % (firstResult["lat"].get("value"),
                                 firstResult["long"].get("value")),
            "result_type": "locality|administrative_area_level_1",
            "key": cherrypy.request.app.config["google"].get("api.key")
        }

        geoQuery = "https://maps.googleapis.com/maps/api/geocode/json?%s" % urllib.parse.urlencode(params)

        with urllib.request.urlopen(geoQuery) as request:
            geoResult = json.loads(request.read().decode("utf-8"))

        return {
            "location": geoResult["results"][0]["formatted_address"],
            "reverseLookup": "http://www.whitepages.com/phone/%s" % (number),
            "wikipedia": "http://en.wikipedia.org/wiki/Area_code_%s" % (areaCode)
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
