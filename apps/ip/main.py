"""Internal and external addressess"""

import json
import typing
import cherrypy


class Controller:
    """Dispatch application requests based on HTTP verb."""

    exposed = True
    show_on_homepage = True

    @staticmethod
    @cherrypy.tools.provides(formats=("json", "text", "html"))
    def GET(*_args: str, **_kwargs: str) -> bytes:
        """Display the client's local IP, and the server's external IP"""

        client_ip = cherrypy.request.headers.get("Remote-Addr")

        if "X-Real-Ip" in cherrypy.request.headers:
            client_ip = cherrypy.request.headers["X-Real-Ip"]

        external_ip = cherrypy.engine.publish(
            "cache:get",
            "ip:external"
        ).pop()

        if not external_ip:
            external_ip = cherrypy.engine.publish(
                "urlfetch:get",
                "https://api.ipify.org",
            ).pop()

            if external_ip:
                cherrypy.engine.publish(
                    "cache:set",
                    "ip:external",
                    external_ip,
                    300
                )

        if cherrypy.request.wants == "json":
            return json.dumps({
                "client_ip": client_ip,
                "external_ip": external_ip,
            }).encode()

        if cherrypy.request.wants == "text":
            return f"client_ip={client_ip}\nexternal_ip={external_ip}".encode()

        return typing.cast(
            bytes,
            cherrypy.engine.publish(
                "jinja:render",
                "ip.jinja.html",
                client_ip=client_ip,
                external_ip=external_ip,
            ).pop()
        )
