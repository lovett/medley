import cherrypy

class Controller:
    """Determine the current IP address"""

    URL = "/ip"

    name = "IP"

    exposed = True

    user_facing = True

    CACHE_KEY = "ip:external"

    @cherrypy.tools.negotiable()
    def GET(self):
        client_ip = cherrypy.request.headers.get("Remote-Addr")

        if "X-Real-Ip" in cherrypy.request.headers:
            client_ip = cherrypy.request.headers["X-Real-Ip"]

        external_ip = cherrypy.engine.publish("cache:get", self.CACHE_KEY).pop()

        if not external_ip:
            external_ip = cherrypy.engine.publish(
                "urlfetch:get",
                "http://myip.dnsomatic.com",
            ).pop()

            if external_ip:
                cherrypy.engine.publish("cache:set", self.CACHE_KEY, external_ip)

        return {
            "json": {
                "client_ip": client_ip,
                "external_ip": external_ip,
            },
            "text": "client_ip={}\nexternal_ip={}".format(client_ip, external_ip),
            "html": ("ip.html", {
                "app_name": self.name,
                "client_ip": client_ip,
                "external_ip": external_ip,
            })
        }
