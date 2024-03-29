"""Import a list of country code abbreviations into the registry."""

import cherrypy


class Controller:
    exposed = True

    show_on_homepage = False

    @staticmethod
    def GET(**kwargs: str) -> None:
        """Request the country code list and populate the registry"""

        source_url = "https://pkgstore.datahub.io" \
            "/core/country-codes/country-codes_json/data" \
            "/471a2e653140ecdd7243cdcacfd66608/country-codes_json.json"

        country_codes, _ = cherrypy.engine.publish(
            "urlfetch:get:json",
            source_url,
            cache_lifespan=86400
        ).pop()

        if not country_codes:
            raise cherrypy.HTTPError(
                501,
                "JSON response contains no country codes"
            )

        for code in country_codes:
            name = code.get("CLDR display name")
            abbrev = code.get("ISO3166-1-Alpha-2")

            if name and abbrev:
                cherrypy.engine.publish(
                    "registry:replace",
                    f"country_code:alpha2:{abbrev}",
                    name
                )

        cherrypy.response.status = 204
