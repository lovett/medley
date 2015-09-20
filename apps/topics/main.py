import sys
import os.path
sys.path.append("../../")

import time
import cherrypy
import tools.negotiable
import tools.jinja
import util.net
import util.db

import urllib.parse
import bs4

class Controller:
    """Scrape news topics from the Bing homepage"""

    exposed = True

    user_facing = True

    @cherrypy.tools.template(template="topics.html")
    @cherrypy.tools.negotiable()
    def GET(self):

        key = "topics_html"
        topics = []

        cached_value = util.db.cacheGet(key)

        if cached_value:
            html = cached_value[0]
            cache_date = cached_value[1]
        else:
            html = util.net.getUrl("http://www.bing.com/hpm")
            util.db.cacheSet(key, html)
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

        return {
            "cache_date": cache_date,
            "topics": topics
        }
