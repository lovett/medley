"""News headlines via News API"""

import cherrypy
import pendulum


class Controller:
    """Dispatch application requests based on HTTP verb."""

    name = "Headlines"

    cache_key = "headlines"

    @cherrypy.tools.negotiable()
    def GET(self, count=30):
        """Display a list of headlines."""

        try:
            count = int(count)
        except ValueError:
            raise cherrypy.HTTPError(400, "Invalid count value")

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
                "count": count,
                "app_name": self.name
            }),
            "json": headlines,
        }
