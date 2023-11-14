"""Look up geographic and network information for an IP address."""

import os.path
import pathlib
import socket
import maxminddb
from typing import Any
from typing import Optional
from typing import Dict
import cherrypy


class Plugin(cherrypy.process.plugins.SimplePlugin):
    """A CherryPy plugin for looking up information about an IP address."""

    def __init__(self, bus: cherrypy.process.wspbus.Bus) -> None:
        cherrypy.process.plugins.SimplePlugin.__init__(self, bus)

    def start(self) -> None:
        """Define the CherryPy messages to listen for.

        This plugin owns the ip prefix.
        """
        self.bus.subscribe("ip:db:modified", self.db_modified)
        self.bus.subscribe("ip:facts", self.facts)
        self.bus.subscribe("ip:reverse", self.reverse)

    @staticmethod
    def db_path() -> pathlib.Path:
        """The filesystem path to the GeoLite2-City database."""

        return pathlib.Path(os.path.join(
            cherrypy.config.get("database_dir"),
            "GeoLite2-City.mmdb"
        ))

    def db_modified(self) -> float:
        """Return the last-modified date of the current database."""

        geodb_path = self.db_path()

        if geodb_path.is_file():
            return geodb_path.stat().st_mtime

        return 0

    def facts(self, ip_address: str) -> Dict[str, str]:
        """Look up geographic information for an IP address."""

        facts: Dict[str, Any] = {
            "annotations": [],
            "geo": {
                "city": "",
                "country_code": "",
                "country_name": "",
                "region_code": "",
                "latitude": "",
                "longitude": "",
                "metro_code": "",
                "map_region": ""
            }
        }

        _, rows = cherrypy.engine.publish(
            "registry:search",
            f"ip:{ip_address}"
        ).pop()

        if rows:
            facts["annotations"] = [
                (row["value"], row["rowid"])
                for row in rows
            ]

        geodb_path = self.db_path()

        try:
            reader = maxminddb.open_database(str(geodb_path))
            result = reader.get(ip_address)
        except (ValueError, FileNotFoundError):
            pass

        if result:

            try:
                facts["geo"]["city"] = result["city"]["names"]["en"]
            except KeyError:
                pass

            try:
                facts["geo"]["country_code"] = result["country"]["iso_code"]
            except KeyError:
                pass

            try:
                facts["geo"]["country_name"] = result["country"]["names"]["en"]
            except KeyError:
                pass

            try:
                facts["geo"]["region_code"] = result["subdivisions"][0]["iso_code"]
            except (IndexError, KeyError):
                pass

            try:
                facts["geo"]["latitude"] = result["location"]["latitude"]
                facts["geo"]["longitude"] = result["location"]["longitude"]
                facts["geo"]["metro_code"] = result["location"]["metro_code"]
            except (KeyError):
                pass

        # Google charts
        facts["geo"]["map_region"] = facts["geo"]["country_code"]
        if facts["geo"]["country_code"] == "US":
            if facts["geo"]["region_code"]:
                country_code = facts["geo"]["country_code"]
                region_code = facts["geo"]["region_code"]
                facts["geo"]["map_region"] = f"{country_code}-{region_code}"

        return facts

    @staticmethod
    def reverse(ip_address: str) -> Dict[str, Any]:
        """Look up the reverse host and domain for an IP address.

        These are treated as separate values because the reverse host
        may embed the IP (reversed or otherwise). The non-IP parts are
        the more interesting ones.

        """

        facts: Dict[str, Any] = {
            "reverse_host": "",
            "reverse_domain": ""
        }

        reverse_host = socket.getfqdn(ip_address)

        if reverse_host != ip_address:
            # Reverse by IPv4 quads (12.34.56.78 becomes 78.56.34.21)
            quads = ip_address.split(".")
            reversed_ip = ".".join(quads[::-1])
            zero_filled_quads = (x.zfill(30) for x in quads)
            dotted_quads = ".".join(zero_filled_quads)
            undotted_quads = dotted_quads.replace(".", "")

            ip_representations = {
                ip_address,
                ip_address.replace(".", ""),
                ip_address.replace(".", "-"),
                ip_address.replace(":", ""),
                ip_address.replace(":", "-"),
                reversed_ip,
                reversed_ip.replace(".", ""),
                reversed_ip.replace(".", "-"),
                dotted_quads,
                undotted_quads,
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
