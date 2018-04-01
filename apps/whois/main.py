"""Look up whois and geoip details for an IP address or hostname."""

import ipaddress
import re
import socket
import urllib.parse
import cherrypy


class Controller:
    """Dispatch application requests based on HTTP verb."""

    name = "Whois"

    exposed = True

    user_facing = True

    @cherrypy.tools.negotiable()
    def GET(self, address=None):
        """Display a search form and lookup results."""

        if not address:
            return {
                "html": ("whois.html", {
                    "app_name": self.name
                })
            }

        address_unquoted = urllib.parse.unquote_plus(address).lower()

        # The address could be an IP or a hostname
        try:
            address_clean = re.sub(r"[^\w.-\/:?]", "", address_unquoted)
            ip_address = str(ipaddress.ip_address(address_clean))
        except ValueError:
            ip_address = None

        if not ip_address:
            address_parsed = urllib.parse.urlparse(address_unquoted)
            address_clean = address_parsed.hostname or address_parsed.path

        if address_clean and not ip_address:
            try:
                result = socket.gethostbyname_ex(address_clean)
                ip_address = result[2][0]
            except OSError:
                redirect_url = cherrypy.engine.publish(
                    "url:for_controller",
                    self
                ).pop()
                raise cherrypy.HTTPRedirect(redirect_url)

        whois_cache_key = "whois:{}".format(ip_address)

        whois = cherrypy.engine.publish("cache:get", whois_cache_key).pop()

        if not whois:
            whois = cherrypy.engine.publish(
                "urlfetch:get",
                "http://whois.arin.net/rest/ip/{}".format(ip_address),
                as_json=True
            ).pop()

            if whois:
                cherrypy.engine.publish("cache:set", whois_cache_key, whois)

        facts_cache_key = "ipfacts:{}".format(ip_address)
        facts = cherrypy.engine.publish("cache:get", facts_cache_key).pop()

        if not facts:
            facts = cherrypy.engine.publish("ip:facts", ip_address).pop()

            if facts:
                cherrypy.engine.publish("cache:set", facts_cache_key, facts)

        return {
            "html": ("whois.html", {
                "address": address_clean,
                "ip_address": ip_address,
                "whois": whois,
                "ip_facts": facts,
                "app_name": self.name
            })
        }
