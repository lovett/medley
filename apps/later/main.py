import sys
import os.path
sys.path.append("../../")

import re
import cherrypy
import tools.jinja
import requests
import util.db
import apps.archive.models
import util.html
import urllib.parse

class Controller:
    """Display a form for bookmarking a URL"""

    exposed = True

    user_facing = True

    @cherrypy.tools.template(template="later.html")
    @cherrypy.tools.negotiable()
    def GET(self, url=None, title=None, tags=None, comments=None):
        error = None
        bookmark = None
        archive = apps.archive.models.Archive()

        if title:
            title = util.html.parse_text(title)
            title = archive.reduceHtmlTitle(title)

        if tags:
            tags = util.html.parse_text(tags)

        if comments:
            comments = util.html.parse_text(comments)
            comments = re.sub("\s+", " ", comments).strip()
            comments = re.sub(",(\w)", ", \\1", comments)

        if comments and not comments.endswith("."):
            comments += "."

        if url:
            bookmark = archive.find(url=url)

        if bookmark:
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
