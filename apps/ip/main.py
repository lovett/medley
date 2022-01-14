"""Internal and external addresses"""

import json
import cherrypy


class Controller:
    """Dispatch application requests based on HTTP verb."""

    exposed = True
    show_on_homepage = True

    @staticmethod
    @cherrypy.tools.provides(formats=("json", "text", "html"))
    def GET(**_kwargs: str) -> bytes:
        """Display the client's local IP, and the server's external IP"""

        client_ip = cherrypy.request.headers.get("Remote-Addr")

        if "X-Real-Ip" in cherrypy.request.headers:
            client_ip = cherrypy.request.headers["X-Real-Ip"]

        api_response = cherrypy.engine.publish(
            "urlfetch:get:json",
            "https://api.ipify.org",
            params={"format": "json"},
            cache_lifespan=86400
        ).pop()

        external_ip = None
        if api_response:
            external_ip = api_response.get("ip")

        if cherrypy.request.wants == "json":
            return json.dumps({
                "client_ip": client_ip,
                "external_ip": external_ip,
            }).encode()

        if cherrypy.request.wants == "text":
            return f"client_ip={client_ip}\nexternal_ip={external_ip}".encode()

        return cherrypy.engine.publish(
            "jinja:render",
            "apps/ip/ip.jinja.html",
            client_ip=client_ip,
            external_ip=external_ip,
        ).pop()
