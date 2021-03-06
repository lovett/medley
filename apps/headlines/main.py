"""News headlines via News API"""

import json
import typing
import cherrypy


class Controller:
    """Dispatch application requests based on HTTP verb."""

    exposed = True
    show_on_homepage = True

    @staticmethod
    @cherrypy.tools.provides(formats=("html",))
    def GET(*_args: str, **kwargs: str) -> bytes:
        """Display a list of headlines."""

        walk_start = int(kwargs.get("start", 1))
        walk_stop = walk_start + int(kwargs.get("count", 40)) - 1

        cache_lifespan = typing.cast(
            int,
            cherrypy.engine.publish(
                "clock:day:remaining"
            ).pop()
        )

        headlines_json = cherrypy.engine.publish(
            "cache:get",
            "headlines"
        ).pop()

        headlines = json.loads(headlines_json) if headlines_json else None

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
                json.dumps(headlines),
                cache_lifespan
            )

        cache_control = f"private, max-age={cache_lifespan}"
        cherrypy.response.headers["Cache-Control"] = cache_control

        return typing.cast(
            bytes,
            cherrypy.engine.publish(
                "jinja:render",
                "apps/headlines/headlines.jinja.html",
                headlines=headlines,
                walk_start=walk_start,
                walk_stop=walk_stop,
            ).pop()
        )
