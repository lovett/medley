"""News headlines via News API"""

import cherrypy
import pendulum


class Controller:
    """Dispatch application requests based on HTTP verb."""

    exposed = True
    show_on_homepage = True

    @staticmethod
    @cherrypy.tools.provides(formats=("html",))
    def GET(*_args, **kwargs):
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
            "headlines"
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
                "headlines",
                headlines,
                cache_lifespan
            )

        cache_control = f"private, max-age={cache_lifespan}"
        cherrypy.response.headers["Cache-Control"] = cache_control

        return cherrypy.engine.publish(
            "jinja:render",
            "headlines.jinja.html",
            headlines=headlines,
            limit=limit,
            offset=offset,
        ).pop()
