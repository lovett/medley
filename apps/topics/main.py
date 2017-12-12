import datetime
import time
import email.utils
import cherrypy
import apps.topics.parser

class Controller:
    """Scrape news topics from the Bing homepage"""

    name = "Topics"

    exposed = True

    user_facing = True

    cache_key = "topics:html"

    @cherrypy.tools.negotiable()
    def GET(self, count=20):
        topics = []

        try:
            count = int(count)
        except ValueError:
            raise cherrypy.HTTPError(400, "Invalid count value")

        # The local server time as a timezone-aware datetime
        now_local = datetime.datetime.now(datetime.timezone.utc).astimezone()

        start_of_today = now_local.replace(hour=0, minute=0, second=0, microsecond=0)

        start_of_tomorrow = start_of_today + datetime.timedelta(days=1, seconds=1)

        start_of_tomorrow_utc = start_of_tomorrow.astimezone(tz=datetime.timezone.utc)

        cache_lifespan = (start_of_tomorrow - now_local).total_seconds()

        answer = cherrypy.engine.publish("cache:get", self.cache_key)
        html = answer.pop() if answer else None

        if not html:
            answer = cherrypy.engine.publish("urlfetch:get", "http://www.bing.com/hpm")
            html = answer.pop() if answer else None

            if not html:
                raise cherrypy.HTTPError(503)

            cherrypy.engine.publish("cache:set", self.cache_key, html, cache_lifespan)

        p = apps.topics.parser.LinkParser()
        p.feed(html)
        p.close()

        topics = p.results

        while len(topics) > 0 and len(topics) < count:
            limit = min(len(topics), count - len(topics))
            topics.extend(topics[0:limit])

        if len(topics) > count:
            topics = topics[0:count]

        cherrypy.response.headers["Expires"] = email.utils.format_datetime(
            start_of_tomorrow_utc,
            usegmt=True
        )

        return {
            "html": ("topics.html", {
                "topics": topics,
                "count": count,
                "app_name": self.name
            }),
            "json": topics,
        }
