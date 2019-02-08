"""Look up whois and geoip details for an IP address or hostname."""

import ipaddress
import re
import socket
import urllib.parse
import cherrypy


class Controller:
    """Dispatch application requests based on HTTP verb."""

    name = "Whois"

    @cherrypy.tools.negotiable()
    def GET(self, *args, **kwargs):
        """Display a search form and lookup results."""

        address = kwargs.get('address')
        if args:
            address = args[-1]

        if not address:
            return {
                "html": ("whois.jinja.html", {})
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
                redirect_url = cherrypy.engine.publish("url:internal").pop()
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

            reverse_ip = cherrypy.engine.publish(
                "ip:reverse",
                ip_address
            ).pop()

            facts.update(reverse_ip)

            cherrypy.engine.publish("cache:set", facts_cache_key, facts)

        visit_days = cherrypy.engine.publish(
            "logindex:count_visit_days",
            ip_address
        ).pop()

        visitors_url = cherrypy.engine.publish(
            "url:internal",
            "/visitors",
            {"query": "ip {}".format(ip_address)}
        ).pop()

        return {
            "html": ("whois.jinja.html", {
                "address": address_clean,
                "ip_address": ip_address,
                "whois": whois,
                "ip_facts": facts,
                "visitors_url": visitors_url,
                "earliest_visit": visit_days.get("earliest"),
                "latest_visit": visit_days.get("latest"),
                "visit_days_count": visit_days.get("count", 0)
            })
        }
