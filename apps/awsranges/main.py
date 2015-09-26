import sys
import os.path
sys.path.append("../../")

import cherrypy
import requests

import util.db
import apps.registry.models
import syslog

class Controller:
    """Download the current set of AWS IP ranges and store in registry.
    Previously downloaded ranges are removed.  See
    http://docs.aws.amazon.com/general/latest/gr/aws-ip-ranges.html
    """

    exposed = True

    user_facing = False

    @cherrypy.tools.encode()
    def GET(self):

        ranges = None
        cache_key = "aws_ranges"
        cached_value = util.db.cacheGet(cache_key)

        if cached_value:
            ranges = cached_value[0]
        else:
            ranges = self.fetch("https://ip-ranges.amazonaws.com/ip-ranges.json")
            util.db.cacheSet(cache_key, ranges)

        if not ranges or not "prefixes" in ranges:
            raise cherrypy.HTTPError(400, "JSON response contains no prefixes")

        registry_key = "netblock:aws"

        registry = apps.registry.models.Registry()

        registry.remove(registry_key)

        for prefix in ranges["prefixes"]:
            registry.add(registry_key, prefix["ip_prefix"])

        syslog.syslog(syslog.LOG_NOTICE, "AWS netblock range download complete")
        cherrypy.response.status = 204
        return

    def fetch(self, url):
        r = requests.get(
            url,
            timeout=5,
            allow_redirects=False,
            headers = {
                "User-Agent": "python"
            }
        )

        r.raise_for_status()
        return r.json()
