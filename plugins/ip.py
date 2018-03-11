import cherrypy
import ipaddress
import os.path
import pygeoip
import socket
from collections import defaultdict
import re

class Plugin(cherrypy.process.plugins.SimplePlugin):

    def __init__(self, bus):
        cherrypy.process.plugins.SimplePlugin.__init__(self, bus)

    def start(self):
        self.bus.subscribe("ip:facts", self.facts)
        self.bus.subscribe("ip:reverse", self.reverse)

    def stop(self):
        pass

    def facts(self, ip):
        facts = defaultdict()

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
        geodb_record = geodb.record_by_addr(ip) or {}
        facts["geo"] = geodb_record

        # Google charts
        try:
            map_region = geodb_record.get("country_code")
            region_code = geodb_record.get("region_code")
            if map_region == "US" and region_code:
                map_region += "-" + region_code
            facts["map_region"] = map_region
        except:
            pass


        return facts


    def reverse(self, ip):
        # Reverse host and domain
        #
        # These are treated as separate values because the reverse host
        # may embed the IP (reversed or otherwise). The non-IP parts are
        # the more interesting ones.

        facts = defaultdict()

        reverse_host = socket.getfqdn(ip)

        if reverse_host != ip:
            # Reverse by IPv4 quads (12.34.56.78 becomes 78.56.34.21)
            quads = ip.split(".")
            reversed_ip = ".".join(quads[::-1])
            zero_filled_quads = tuple(map(lambda x: x.zfill(3), quads))

            ip_representations = {
                ip,
                ip.replace(".", ""),
                ip.replace(".", "-"),
                ip.replace(":", ""),
                ip.replace(":", "-"),
                reversed_ip,
                reversed_ip.replace(".", ""),
                reversed_ip.replace(".", "-"),
                ".".join(zero_filled_quads),
                "".join(zero_filled_quads),
            }

            filtered_reverse_host = reverse_host
            replacement_placeholder = "~PLACEHOLDER~"
            for rep in ip_representations:
                filtered_reverse_host = filtered_reverse_host.replace(
                    rep, replacement_placeholder
                )

            filtered_segments = filter(
                lambda x: replacement_placeholder not in x,
                filtered_reverse_host.split(".")
            )

            reverse_domain = ".".join(filtered_segments)

            facts["reverse_host"] = reverse_host
            facts["reverse_domain"] = reverse_domain

        return facts
