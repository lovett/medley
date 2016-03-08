import cherrypy
import requests

import util.cache
import apps.registry.models
import syslog

class Controller:
    """Import a list of country code abbreviations into the registry"""

    name = "Country Codes"

    exposed = True

    user_facing = False

    @cherrypy.tools.encode()
    def GET(self):
        cache = util.cache.Cache()

        codes = None
        cache_key = "country_codes"
        cached_value = cache.get(cache_key)

        if cached_value:
            codes = cached_value[0]
        else:
            codes = self.fetch("http://data.okfn.org/data/core/country-codes/r/country-codes.json")
            cache.set(cache_key, codes)

        if not codes:
            raise cherrypy.HTTPError(400, "JSON response contains no country codes")

        registry = apps.registry.models.Registry()

        for code in codes:
            key = "country_code:alpha2:{}".format(code["ISO3166-1-Alpha-2"])
            registry.add(key, code["name"], True)

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
