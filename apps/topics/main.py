import datetime
import email.utils
import time
import cherrypy
import requests
import util.cache
import apps.topics.parser

class Controller:
    """Scrape news topics from the Bing homepage"""

    name = "Topics"

    exposed = True

    user_facing = True

    @cherrypy.tools.template(template="topics.html")
    @cherrypy.tools.negotiable()
    def GET(self, count=15):
        max_age_hours = 18
        cache = util.cache.Cache()
        key = "topics_html"
        topics = []
        try:
            count = int(count)
        except ValueError:
            raise cherrypy.HTTPError(400, "Invalid count value")

        cached_value = cache.get(key)

        if cached_value:
            html = cached_value[0]
            cache_date = datetime.datetime.strptime(cached_value[1], "%Y-%m-%d %H:%M:%S")
        else:
            html = self.fetch("http://www.bing.com/hpm")
            cache.set(key, html, 60 * 60 * max_age_hours)
            cache_date = datetime.datetime.utcnow()

        p = apps.topics.parser.LinkParser()
        p.feed(html)
        p.close()

        topics = p.results

        while len(topics) > 0 and len(topics) < count:
            limit = min(len(topics), count - len(topics))
            topics.extend(topics[0:limit])

        if len(topics) > count:
            topics = topics[0:count]

        expiration = cache_date + datetime.timedelta(hours=max_age_hours)
        expiration = time.mktime(expiration.timetuple())
        cherrypy.response.headers["Expires"] = email.utils.formatdate(
            timeval=expiration,
            localtime=False,
            usegmt=True
        )

        return {
            "cache_date": cache_date,
            "topics": topics,
            "count": count,
            "app_name": self.name
        }

    def fetch(self, url):
        r = requests.get(
            url,
            timeout=5,
            allow_redirects=False,
            headers = {
                "User-Agent": "python"
            }
        )

        r.raise_for_status()
        return r.text
