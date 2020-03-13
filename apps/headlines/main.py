"""News headlines via News API"""

import typing
import cherrypy
import pendulum


class Controller:
    """Dispatch application requests based on HTTP verb."""

    exposed = True
    show_on_homepage = True

    @staticmethod
    @cherrypy.tools.provides(formats=("html",))
    def GET(*_args: str, **kwargs: str) -> bytes:
        """Display a list of headlines."""

        limit = int(kwargs.get("limit", 40))
        offset = int(kwargs.get("offset", 1))

        now = pendulum.now()

        cache_lifespan = (now.end_of('day') - now).in_seconds()

        headlines = cherrypy.engine.publish(
            "cache:get",
            "headlines"
        ).pop()

        if not headlines:
            headlines = {}

            settings = cherrypy.engine.publish(
                "registry:search:multidict",
                key="newsapi:*",
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
                "headlines",
                headlines,
                cache_lifespan
            )

        cache_control = f"private, max-age={cache_lifespan}"
        cherrypy.response.headers["Cache-Control"] = cache_control

        return typing.cast(
            bytes,
            cherrypy.engine.publish(
                "jinja:render",
                "headlines.jinja.html",
                headlines=headlines,
                limit=limit,
                offset=offset,
            ).pop()
        )
