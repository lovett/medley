"""News stories"""

import cherrypy
from resources.url import Url


class Controller:
    exposed = True
    show_on_homepage = True
    cache_lifespan = 60 * 60 * 6

    @cherrypy.tools.provides(formats=("html",))
    @cherrypy.tools.etag()
    def GET(self, **kwargs: str) -> bytes:
        """Display a list of headlines."""

        start = int(kwargs.get("start", 1))
        count = int(kwargs.get("count", 40))

        settings = cherrypy.engine.publish(
            "registry:search:multidict",
            key="newsapi:*",
            key_slice=1
        ).pop()

        headlines = {
            category: None
            for category in settings["category"]
        }

        cache_info = None

        for category in settings["category"]:
            endpoint = Url(
                "https://newsapi.org/v2/top-headlines",
                query={
                    "country": settings["country"][0],
                    "apiKey": settings["key"][0],
                    "category": category
                }
            )
            precached = cherrypy.engine.publish(
                "urlfetch:precache",
                endpoint,
                cache_lifespan=self.cache_lifespan
            ).pop()

            if not precached:
                raise cherrypy.HTTPError(503)

            if not cache_info:
                cache_info = cherrypy.engine.publish(
                    "cache:info",
                    endpoint.address,
                ).pop()

            headlines[category] = cherrypy.engine.publish(
                "cache:headlines",
                endpoint
            ).pop()

        return cherrypy.engine.publish(
            "jinja:render",
            "apps/headlines/headlines.jinja.html",
            headlines=headlines,
            walk_start=start,
            walk_stop=(start + count - 1),
            ms_rewards=Url("https://rewards.bing.com/?signin=1"),
            bing=Url("https://www.bing.com"),
            **cache_info
        ).pop()
