import cherrypy
import ipaddress
import os.path
import pygeoip
import socket

class Plugin(cherrypy.process.plugins.SimplePlugin):

    def __init__(self, bus):
        cherrypy.process.plugins.SimplePlugin.__init__(self, bus)

    def start(self):
        self.bus.subscribe("ip:facts", self.facts)

    def stop(self):
        pass

    def facts(self, ip):
        facts = {}

        address = ipaddress.ip_address(ip)

        netblocks = cherrypy.engine.publish(
            "registry:search",
            "netblock:*"
        ).pop()

        for netblock in netblocks:
            if address in ipaddress.ip_network(netblock["value"]):
                facts["organization"] = netblock["key"].split(":")[1]
                break

        annotations = cherrypy.engine.publish(
            "registry:search",
            "ip:{}".format(ip)
        ).pop()

        if annotations:
            facts["annotations"] = [(a["value"], a["rowid"]) for a in annotations]

        geodb_download_url = cherrypy.engine.publish(
            "registry:first_value",
            "geodb:download_url"
        ).pop()

        geodb_path = os.path.join(
            cherrypy.config.get("database_dir"),
            os.path.basename(geodb_download_url)
        )

        if geodb_path.endswith(".gz"):
            geodb_path = geodb_path[0:-3]

        geodb = pygeoip.GeoIP(geodb_path)
        geodb_record = geodb.record_by_addr(ip)
        facts["geo"] = geodb_record

        # Google charts
        try:
            map_region = geodb_record.get("country_code")
            region_code = geodb_record.get("region_code")
            if map_region == "US" and region_code:
                map_region += "-" + region_code
        except:
            map_region = None

        facts["map_region"] = map_region

        try:
            facts["reverse_host"] = socket.gethostbyaddr(ip)[0]
        except:
            facts["reverse_host"] = None


        return facts
