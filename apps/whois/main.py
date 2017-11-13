import re
import cherrypy
import urllib.parse
import socket
import ipaddress

class Controller:
    """Whois and geoip data for an IP address or hostname"""

    url = "/whois"

    name = "Whois"

    exposed = True

    user_facing = True

    @cherrypy.tools.negotiable()
    def GET(self, address=None):
        if not address:
            return {
                "html": ("whois.html", {
                "app_name": self.name
                })
            }

        try:
            address_unquoted = urllib.parse.unquote_plus(address).lower()
        except:
            address_unquoted = None

        # The address could be an IP or a hostname
        try:
            address_clean = re.sub(r"[^\w.-\/:?]", "", address_unquoted)
            ip = str(ipaddress.ip_address(address_clean))
        except ValueError:
            address_parsed = urllib.parse.urlparse(address_unquoted)
            if "hostname" in address_parsed:
                address_clean = address_parsed.hostname
            elif "path" in address_parsed:
                address_clean = address_parsed.path

            if not address_clean:
                raise ValueError

            result = socket.gethostbyname_ex(address_clean)
            ip = result[2][0]
        except:
            raise cherrypy.HTTPRedirect(self.url)

        whois_cache_key = "whois:{}".format(ip)

        whois = cherrypy.engine.publish("cache:get", whois_cache_key).pop()

        if not whois:
            whois = cherrypy.engine.publish(
                "urlfetch:get",
                "http://whois.arin.net/rest/ip/{}".format(ip),
                as_json=True
            ).pop()

            if whois:
                cherrypy.engine.publish("cache:set", whois_cache_key, whois)


        facts_cache_key = "ipfacts:{}".format(ip)
        facts = cherrypy.engine.publish("cache:get", facts_cache_key).pop()

        if not facts:
            facts = cherrypy.engine.publish("ip:facts", ip).pop()

            if facts:
                cherrypy.engine.publish("cache:set", facts_cache_key, facts)

        return {
            "html": ("whois.html", {
                "address": address_clean,
                "ip": ip,
                "whois": whois,
                "ip_facts": facts,
                "app_name": self.name
            })
        }
