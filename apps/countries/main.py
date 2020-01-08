"""Import a list of country code abbreviations into the registry."""

import cherrypy


class Controller:
    """Dispatch application requests based on HTTP verb."""

    exposed = True

    show_on_homepage = False

    @staticmethod
    def GET(*_args, **_kwargs) -> None:
        """Request the country code list and populate the registry"""

        country_codes = cherrypy.engine.publish(
            "cache:get",
            "countries"
        ).pop()

        if not country_codes:
            source_url = "https://pkgstore.datahub.io" \
                "/core/country-codes/country-codes_json/data" \
                "/471a2e653140ecdd7243cdcacfd66608/country-codes_json.json"

            country_codes = cherrypy.engine.publish(
                "urlfetch:get",
                source_url,
                as_json=True
            ).pop()

            if country_codes:
                cherrypy.engine.publish(
                    "cache:set",
                    "countries",
                    country_codes
                )

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
                    "registry:add",
                    f"country_code:alpha2:{abbrev}",
                    (name,),
                    True
                )

        cherrypy.response.status = 204
