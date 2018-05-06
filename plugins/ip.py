"""Look up geographic and network information for an IP address."""

import os.path
import socket
from collections import defaultdict
import cherrypy
import geoip2.database


class Plugin(cherrypy.process.plugins.SimplePlugin):
    """A CherryPy plugin for looking up information about an IP address."""

    def __init__(self, bus):
        cherrypy.process.plugins.SimplePlugin.__init__(self, bus)

    def start(self):
        """Define the CherryPy messages to listen for.

        This plugin owns the ip prefix.
        """
        self.bus.subscribe("ip:facts", self.facts)
        self.bus.subscribe("ip:reverse", self.reverse)

    @staticmethod
    def facts(ip_address):
        """Look up geographic information for an IP address."""

        annotations = cherrypy.engine.publish(
            "registry:search",
            "ip:{}".format(ip_address)
        ).pop()

        facts = defaultdict()

        if annotations:
            facts["annotations"] = [
                (a["value"], a["rowid"])
                for a in annotations
            ]

        geodb_path = os.path.join(
            cherrypy.config.get("database_dir"),
            "GeoLite2-City.mmdb"
        )

        geodb = geoip2.database.Reader(geodb_path)

        facts["geo"] = geodb.city(ip_address) or {}

        # Google charts
        map_region = facts["geo"].get("country_code", "")
        region_code = facts["geo"].get("region_code", "")
        if map_region == "US" and region_code:
            facts["map_region"] = "{}-{}".format(
                map_region,
                region_code
            )

        return facts

    @staticmethod
    def reverse(ip_address):
        """Look up the reverse host and domain for an IP address.

        These are treated as separate values because the reverse host
        may embed the IP (reversed or otherwise). The non-IP parts are
        the more interesting ones.

        """

        facts = defaultdict()

        reverse_host = socket.getfqdn(ip_address)

        if reverse_host != ip_address:
            # Reverse by IPv4 quads (12.34.56.78 becomes 78.56.34.21)
            quads = ip_address.split(".")
            reversed_ip = ".".join(quads[::-1])
            zero_filled_quads = tuple(map(lambda x: x.zfill(3), quads))

            ip_representations = {
                ip_address,
                ip_address.replace(".", ""),
                ip_address.replace(".", "-"),
                ip_address.replace(":", ""),
                ip_address.replace(":", "-"),
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
