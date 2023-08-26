"""News stories"""

import cherrypy
from resources.url import Url


class Controller:
    exposed = True
    show_on_homepage = True

    @staticmethod
    @cherrypy.tools.provides(formats=("html",))
    def GET(**kwargs: str) -> bytes:
        """Display a list of headlines."""

        start = int(kwargs.get("start", 1))
        count = int(kwargs.get("count", 40))

        cache_lifespan = cherrypy.engine.publish(
            "clock:day:remaining"
        ).pop()

        headlines = {}

        settings = cherrypy.engine.publish(
            "registry:search:multidict",
            key="newsapi:*",
            key_slice=1
        ).pop()

        cached_on = None
        for category in settings["category"]:
            response, cached_on = cherrypy.engine.publish(
                "urlfetch:get:json",
                "https://newsapi.org/v2/top-headlines",
                params={
                    "country": settings["country"][0],
                    "apiKey": settings["key"][0],
                    "category": category
                },
                cache_lifespan=cache_lifespan
            ).pop()

            if not response:
                raise cherrypy.HTTPError(503)

            headlines[category] = [
                Url(article["url"], article["title"])
                for article in response["articles"]
            ]

        cache_control = f"private, max-age={cache_lifespan}"
        cherrypy.response.headers["Cache-Control"] = cache_control

        return cherrypy.engine.publish(
            "jinja:render",
            "apps/headlines/headlines.jinja.html",
            headlines=headlines,
            walk_start=start,
            walk_stop=(start + count - 1),
            bing=Url("https://www.bing.com"),
            ms_rewards=Url("https://rewards.bing.com/?signin=1"),
            cached_on=cached_on
        ).pop()
