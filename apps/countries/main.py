"""Import a list of country code abbreviations into the registry."""

import cherrypy


class Controller:
    """Dispatch application requests based on HTTP verb."""

    user_facing = False

    cache_key = "countries"

    registry_key = "country_code:alpha2:{}"

    source_url = "https://pkgstore.datahub.io" \
                 "/core/country-codes/country-codes_json/data" \
                 "/471a2e653140ecdd7243cdcacfd66608/country-codes_json.json"

    @staticmethod
    def name_and_abbrev(code):
        """Extract the name and 2-letter abbreviation from a country code."""

        name = code.get("official_name_en")
        abbrev = code.get("ISO3166-1-Alpha-2")

        # Shorten long names.
        if name:
            name = name.split(" (")[0]

            if name.startswith("Russian Federation"):
                name = "Russia"

            if name.startswith("Republic of Korea"):
                name = "Korea"

            if name.startswith("United Kingdom of"):
                name = "UK"

            if name == "United States of America":
                name = "USA"

        return (name, abbrev)

    def GET(self, *_args, **_kwargs):
        """Request the country code list and populate the registry"""

        country_codes = cherrypy.engine.publish(
            "cache:get",
            self.cache_key
        ).pop()

        if not country_codes:
            country_codes = cherrypy.engine.publish(
                "urlfetch:get",
                self.source_url,
                as_json=True
            ).pop()

            if country_codes:
                cherrypy.engine.publish(
                    "cache:set",
                    self.cache_key,
                    country_codes
                )

        if not country_codes:
            raise cherrypy.HTTPError(
                501,
                "JSON response contains no country codes"
            )

        for code in country_codes:
            name, abbrev = self.name_and_abbrev(code)
            if name and abbrev:
                key = self.registry_key.format(abbrev)
                cherrypy.engine.publish("registry:add", key, (name,), True)

        cherrypy.response.status = 204
