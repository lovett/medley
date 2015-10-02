import sys
import os.path
sys.path.append("../../")

import re
import cherrypy
import tools.jinja
import requests
import util.db
import util.html
import urllib.parse

class Controller:
    """Display a form for bookmarking a URL"""

    exposed = True

    user_facing = True

    def POST(self, url, title=None, tags=None, comments=None):

        page = self.fetch(url)

        if not title:
            title = getHtmlTitle(page)
            title = self.reduceHtmlTitle(title)

        url_id = util.db.saveBookmark(url, title, comments, tags)

        if page:
            text = util.net.htmlToText(page)
            util.db.saveBookmarkFulltext(url_id, text)

        cherrypy.response.code = 204

    @cherrypy.tools.template(template="later.html")
    @cherrypy.tools.negotiable()
    def GET(self, url=None, title=None, tags=None, comments=None):
        error = None
        bookmark = None

        if title:
            title = util.html.parse_text(title)
            title = self.reduceHtmlTitle(title)

        if tags:
            tags = util.html.parse_text(tags)

        if comments:
            comments = util.html.parse_text(comments)
            comments = re.sub("\s+", " ", comments).strip()
            comments = re.sub(",(\w)", ", \\1", comments)

        if comments and not comments.endswith("."):
            comments += "."

        if url:
            bookmark = util.db.getBookmarkByUrl(url)
            print("ok")

        if bookmark:
            print("yes")
            error = "This URL has already been bookmarked"
            title = util.html.parse_text(bookmark["title"])
            tags = util.html.parse_text(bookmark["tags"])
            comments = util.html.parse_text(bookmark["comments"])



        return {
            "base": cherrypy.config.get("base"),
            "error": error,
            "title": title,
            "url": url,
            "tags": tags,
            "comments": comments
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

    def reduceHtmlTitle(self, title):
        """Remove site identifiers and noise from the title of an HTML document"""
        title = title or ""
        reduced_title = title
        for char in "|·—:-":
            separator = " {} ".format(char)
            if separator in title:
                segments = title.split(separator)
                reduced_title = max(segments, key=len)
                break

        if reduced_title == title:
            return title
        else:
            return reduceHtmlTitle(reduced_title)
