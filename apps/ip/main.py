"""
Determine the current IP address
"""

import cherrypy


class Controller:
    """
    The primary controller for the application, structured for
    method-based dispatch
    """

    name = "IP"

    exposed = True

    user_facing = True

    cache_key = "ip:external"

    @cherrypy.tools.negotiable()
    def GET(self):
        """Display the client's local IP, and the server's external IP"""

        client_ip = cherrypy.request.headers.get("Remote-Addr")

        if "X-Real-Ip" in cherrypy.request.headers:
            client_ip = cherrypy.request.headers["X-Real-Ip"]

        external_ip = cherrypy.engine.publish(
            "cache:get",
            self.cache_key
        ).pop()

        if not external_ip:
            external_ip = cherrypy.engine.publish(
                "urlfetch:get",
                "http://myip.dnsomatic.com",
            ).pop()

            if external_ip:
                cherrypy.engine.publish(
                    "cache:set",
                    self.cache_key,
                    external_ip
                )

        return {
            "json": {
                "client_ip": client_ip,
                "external_ip": external_ip,
            },
            "text": "client_ip={}\nexternal_ip={}".format(
                client_ip,
                external_ip
            ),
            "html": ("ip.html", {
                "app_name": self.name,
                "client_ip": client_ip,
                "external_ip": external_ip,
            })
        }
