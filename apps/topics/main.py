import time
import cherrypy
import tools.negotiable
import tools.jinja
import requests
import util.cache
import urllib.parse
import bs4

class Controller:
    """Scrape news topics from the Bing homepage"""

    name = "Topics"

    exposed = True

    user_facing = True

    @cherrypy.tools.template(template="topics.html")
    @cherrypy.tools.negotiable()
    def GET(self, count=15):
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
            cache_date = cached_value[1]
        else:
            html = self.fetch("http://www.bing.com/hpm")
            cache.set(key, html, 60 * 60 * 18)
            cache_date = None

        soup = bs4.BeautifulSoup(html, "html.parser")

        container = soup.find(id="crs_pane")

        topics = []
        if container:
            for link in container.find_all("a"):
                url = urllib.parse.urlparse(link["href"])
                qs = urllib.parse.parse_qs(url.query)

                if "q" in qs:
                    topics.append(qs["q"][0])


        while len(topics) < count:
            limit = min(len(topics), count - len(topics))
            topics.extend(topics[0:limit])

        if len(topics) > count:
            topics = topics[0:count]


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
