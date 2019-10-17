"""News headlines via News API"""

import cherrypy
import pendulum


class Controller:
    """Dispatch application requests based on HTTP verb."""

    name = "Headlines"
    exposed = True
    user_facing = True

    cache_key = "headlines"

    @cherrypy.tools.negotiable()
    def GET(self, *_args, **kwargs):
        """Display a list of headlines."""

        limit = kwargs.get('limit')
        offset = kwargs.get('offset')

        try:
            limit = int(limit)
        except (ValueError, TypeError):
            limit = 40

        try:
            offset = int(offset)
        except (ValueError, TypeError):
            offset = 1

        now = pendulum.now()

        cache_lifespan = (now.end_of('day') - now).in_seconds()

        headlines = cherrypy.engine.publish(
            "cache:get",
            self.cache_key
        ).pop()

        if not headlines:
            headlines = {}

            settings = cherrypy.engine.publish(
                "registry:search",
                key="newsapi:*",
                as_multivalue_dict=True,
                key_slice=1
            ).pop()

            for category in settings["category"]:
                response = cherrypy.engine.publish(
                    "urlfetch:get",
                    "https://newsapi.org/v2/top-headlines",
                    as_json=True,
                    params={
                        "country": settings["country"][0],
                        "apiKey": settings["key"][0],
                        "category": category
                    }
                ).pop()

                if not response:
                    raise cherrypy.HTTPError(503)

                headlines[category] = response["articles"]

            cherrypy.engine.publish(
                "cache:set",
                self.cache_key,
                headlines,
                cache_lifespan
            )

        return {
            "max_age": cache_lifespan,
            "html": ("headlines.jinja.html", {
                "headlines": headlines,
                "limit": limit,
                "offset": offset,
            }),
            "json": headlines,
        }
