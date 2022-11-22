"""News headlines via News API"""

import cherrypy
from pydantic import BaseModel
from pydantic import ValidationError
from resources.url import Url


class GetParams(BaseModel):
    """Parameters for GET requests."""
    start: int = 1
    count: int = 40


class Controller:
    """Dispatch application requests based on HTTP verb."""

    exposed = True
    show_on_homepage = True

    @staticmethod
    @cherrypy.tools.provides(formats=("html",))
    def GET(**kwargs: str) -> bytes:
        """Display a list of headlines."""

        try:
            params = GetParams(**kwargs)
        except ValidationError as error:
            raise cherrypy.HTTPError(400) from error

        cache_lifespan = cherrypy.engine.publish(
            "clock:day:remaining"
        ).pop()

        headlines = {}

        settings = cherrypy.engine.publish(
            "registry:search:multidict",
            key="newsapi:*",
            key_slice=1
        ).pop()

        for category in settings["category"]:
            response = cherrypy.engine.publish(
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
            walk_start=params.start,
            walk_stop=(params.start + params.count - 1),
            bing=Url("https://www.bing.com"),
            ms_rewards=Url("https://rewards.bing.com/?signin=1")
        ).pop()
