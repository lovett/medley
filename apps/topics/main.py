"""Scrape news topics from the Bing homepage"""

import cherrypy
import pendulum
import apps.topics.parser


class Controller:
    """Dispatch application requests based on HTTP verb."""

    name = "Topics"

    cache_key = "topics:html"

    @cherrypy.tools.negotiable()
    def GET(self, count=20):
        """Display a list of links."""

        topics = []

        try:
            count = int(count)
        except ValueError:
            raise cherrypy.HTTPError(400, "Invalid count value")

        now = pendulum.now()

        cache_lifespan = (now.end_of('day') - now).in_seconds()

        html = cherrypy.engine.publish(
            "cache:get",
            self.cache_key
        ).pop()

        if not html:
            html = cherrypy.engine.publish(
                "urlfetch:get",
                "http://www.bing.com/hpm"
            ).pop()

            if not html:
                raise cherrypy.HTTPError(503)

            cherrypy.engine.publish(
                "cache:set",
                self.cache_key,
                html,
                cache_lifespan
            )

        parser = apps.topics.parser.LinkParser()
        parser.feed(html)
        parser.close()

        topics = parser.results

        while topics and len(topics) < count:
            limit = min(len(topics), count - len(topics))
            topics.extend(topics[0:limit])

        if len(topics) > count:
            topics = topics[0:count]

        return {
            "max_age": cache_lifespan,
            "html": ("topics.jinja.html", {
                "topics": topics,
                "count": count,
                "app_name": self.name
            }),
            "json": topics,
        }
