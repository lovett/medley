"""IP and domain lookup"""

import ipaddress
import re
import socket
import urllib.parse
import cherrypy
from resources.url import Url


class Controller:
    exposed = True
    show_on_homepage = True

    @staticmethod
    @cherrypy.tools.provides(formats=("html",))
    def GET(**kwargs: str) -> bytes:
        """Display a search form and lookup results."""

        address = kwargs.get("address", "").strip().lower()

        if not address:
            return cherrypy.engine.publish(
                "jinja:render",
                "apps/whois/whois.jinja.html"
            ).pop()

        address_unquoted = urllib.parse.unquote_plus(address)

        # The address could be an IP or a hostname
        try:
            address_clean = re.sub(r"[^\w.-\/:?]", "", address_unquoted)
            ip_address = str(ipaddress.ip_address(address_clean))
        except ValueError:
            ip_address = ""

        if not ip_address:
            address_parsed = Url(address_unquoted)

            try:
                result = socket.gethostbyname_ex(  # pylint: disable=no-member
                    address_parsed.domain
                )
                ip_address = result[2][0]
            except OSError as exc:
                redirect_url = cherrypy.engine.publish("app_url").pop()
                raise cherrypy.HTTPRedirect(redirect_url) from exc

        whois = cherrypy.engine.publish(
            "urlfetch:get:json",
            f"http://whois.arin.net/rest/ip/{ip_address}",
            cache_lifespan=86400
        ).pop()

        facts_cache_key = f"ipfacts:{ip_address}"

        facts = cherrypy.engine.publish(
            "cache:get",
            facts_cache_key
        ).pop()

        if not facts:
            facts = cherrypy.engine.publish("ip:facts", ip_address).pop()

            reverse_ip = cherrypy.engine.publish(
                "ip:reverse",
                ip_address
            ).pop()

            if reverse_ip:
                facts.update(reverse_ip)

            if facts:
                cherrypy.engine.publish(
                    "cache:set",
                    facts_cache_key,
                    facts
                )

        visit_days = cherrypy.engine.publish(
            "logindex:count_visit_days",
            ip_address
        ).pop()

        visitors_url = cherrypy.engine.publish(
            "app_url",
            "/visitors",
            {"query": f"ip {ip_address}"}
        ).pop()

        return cherrypy.engine.publish(
            "jinja:render",
            "apps/whois/whois.jinja.html",
            address=address_clean,
            ip_address=ip_address,
            whois=whois,
            ip_facts=facts,
            visitors_url=visitors_url,
            earliest_visit=visit_days.get("earliest"),
            latest_visit=visit_days.get("latest"),
            visit_days_count=visit_days.get("count", 0),
            subview_title=address_clean
        ).pop()
