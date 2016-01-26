import re
import subprocess
import cherrypy
import tools.negotiable
import tools.jinja
import urllib.parse
import socket
import util.cache
import requests
import util.ip
import ipaddress

class Controller:
    """Display whois and geoip data for an IP address or hostname"""

    exposed = True

    user_facing = True

    @cherrypy.tools.template(template="whois.html")
    @cherrypy.tools.negotiable()
    def GET(self, address=None):
        ip = None
        cache = util.cache.Cache()

        if not address and cherrypy.request.as_json:
            cherrypy.response.status = 400
            return {
                "message": "Address not specified"
            }
        if not address and cherrypy.request.as_text:
            raise cherrypy.HTTPError(400, "Address not specified")

        if not address:
            return {}

        # Sanitization
        address_unquoted = urllib.parse.unquote_plus(address).lower()
        address_clean = re.sub(r"[^\w.-\/:?]", "", address_unquoted)

        # Is the address an IP?
        try:
            ipaddress.ip_address(address_clean)
            ip = address_clean
        except ValueError:
            pass

        # Is the address a hostname?
        if ip is None:
            address_parsed = urllib.parse.urlparse(address_clean)
            if address_parsed.hostname:
                address_clean = address_parsed.hostname
            ip = self.resolveHost(address_clean)

        if ip is None and cherrypy.request.as_text:
            raise cherrypy.HTTPError(400, "Invalid address")

        if ip is None:
            cherrypy.response.status = 400
            return {
                "message": "Invalid address"
            }

        cache_key = "whois:{}".format(address_clean)
        cached_value = cache.get(cache_key)

        if cached_value:
            whois_result = cached_value[0]
        else:
            r = requests.get(
                "http://whois.arin.net/rest/ip/{}".format(ip),
                timeout = 5,
                allow_redirects = False,
                headers = {
                    "User-Agent": "python",
                    "Accept": "application/json"
                }
            )
            r.raise_for_status()
            whois_result = r.json()
            cache.set(cache_key, whois_result)

        ip_facts = util.ip.facts(ip)


        # Google charts
        try:
            map_region = ip_facts["geo"]["country_code"]
            if map_region == "US" and ip_facts["geo"].get("region_code", None):
                map_region += "-" + ip_facts["geo"]["region_code"]
        except:
            map_region = None

        if cherrypy.request.as_text:
            if "city" in ip_facts["geo"] and "country_name" in ip_facts["geo"]:
                return "{}, {}".format(ip_facts["geo"]["city"], ip_facts["geo"]["country_name"])
            elif "country_name" in ip_facts["geo"]:
                return ip_facts["geo"]["country_name"]
            else:
                return "Unknown"

        return {
            "address": address_clean,
            "ip": ip,
            "whois": whois_result,
            "ip_facts": ip_facts,
            "reverse_host": self.reverseLookup(ip),
            "map_region": map_region
        }


    def resolveHost(self, host=None):
        """Resolve a hostname to its IP address"""

        try:
            result = socket.gethostbyname_ex(host)
            return result[2][0]
        except:
            pass

    def reverseLookup(self, ip=None):
        """Find the hostname associated with the given IP"""

        try:
            result = socket.gethostbyaddr(ip)
            return result[0]
        except:
            pass
