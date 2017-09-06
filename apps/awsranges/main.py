import cherrypy

class Controller:
    """Download the current set of AWS IP ranges and store in registry.
    Previously downloaded ranges are removed.

    See http://docs.aws.amazon.com/general/latest/gr/aws-ip-ranges.html"""

    URL = "/awsranges"

    name = "AWS Ranges"

    exposed = True

    user_facing = False

    CACHE_KEY = "awsranges-json"

    REGISTRY_KEY = "netblock:aws"

    @cherrypy.tools.encode()
    def GET(self):
        ranges = cherrypy.engine.publish("cache:get", self.CACHE_KEY).pop()

        if not ranges:
            ranges = cherrypy.engine.publish(
                "urlfetch:get",
                url="https://ip-ranges.amazonaws.com/ip-ranges.json",
                as_json=True,
            ).pop()

            if ranges:
                cherrypy.engine.publish("cache:set", self.CACHE_KEY, ranges)

        if not ranges:
            raise cherrypy.HTTPError(503)

        values = [prefix.get("ip_prefix") for prefix in ranges["prefixes"]]

        cherrypy.engine.publish(
            "registry:add",
            self.REGISTRY_KEY,
            values,
            replace=True
        )

        cherrypy.response.status = 204
        return
