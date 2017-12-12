import cherrypy

class Controller:
    """Import a list of country code abbreviations into the registry"""

    name = "Country Codes"

    exposed = True

    user_facing = False

    cache_key = "countries"

    registry_key = "country_code:alpha2:{}"

    download_url = "http://data.okfn.org/data/core/country-codes/r/country-codes.json"

    def GET(self):
        codes = None

        answer = cherrypy.engine.publish("cache:get", self.cache_key)
        country_codes = answer.pop() if answer else []

        if not country_codes:
            answer = cherrypy.engine.publish(
                "urlfetch:get",
                self.download_url,
                as_json=True
            )
            country_codes = answer.pop() if answer else []

            if country_codes:
                cherrypy.engine.publish("cache:set", self.cache_key, country_codes)

        if not country_codes:
            raise cherrypy.HTTPError(501, "JSON response contains no country codes")

        for code in country_codes:
            key = self.registry_key.format(code["ISO3166-1-Alpha-2"])
            cherrypy.engine.publish("registry:add", key, [code["name"]], True)

        cherrypy.response.status = 204
        return
