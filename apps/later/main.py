"""Bookmark a webpage"""

import re
import cherrypy
from resources.url import Url


class Controller:
    """Dispatch application requests based on HTTP verb."""

    exposed = True
    show_on_homepage = True

    @staticmethod
    @cherrypy.tools.provides(formats=("html",))
    def GET(*_args: str, **kwargs: str) -> bytes:
        """Display a form for for bookmarking a URL"""

        error = None
        url = Url(kwargs.get("url", ""))
        title = kwargs.get("title", "").strip()
        tags = kwargs.get("tags", "").strip()
        comments = kwargs.get("comments", "").strip()

        if title:
            title = cherrypy.engine.publish(
                "markup:plaintext",
                title,
                url
            ).pop()

            title = cherrypy.engine.publish(
                "markup:reduce:title",
                title
            ).pop()

        if tags:
            tags = cherrypy.engine.publish(
                "markup:plaintext",
                tags
            ).pop()

        # Meta description tags on Reddit aren't specific to the URL
        # being bookmarked.
        if "reddit.com" in url.domain:
            if comments.startswith("r/"):
                comments = ""

        if comments:
            comments = cherrypy.engine.publish(
                "markup:plaintext",
                comments
            ).pop()
            comments = re.sub(r"\s+", " ", comments).strip()
            comments = re.sub(r",(\w)", ", \\1", comments)
            comments = ". ".join([
                sentence[0].capitalize() + sentence[1:]
                for sentence in comments.split(". ")
            ])

        if comments and not comments.endswith("."):
            comments += "."

        bookmark = None
        if url:
            bookmark = cherrypy.engine.publish(
                "bookmarks:find:url",
                url
            ).pop()

        if bookmark:
            title = bookmark["title"]
            tags = bookmark["tags"]
            comments = bookmark["comments"]

        bookmarks_url = cherrypy.engine.publish(
            "url:internal",
            "/bookmarks",
            {"query": title, "order": "date-desc"}
        ).pop()

        return cherrypy.engine.publish(
            "jinja:render",
            "apps/later/later.jinja.html",
            bookmarks_url=bookmarks_url,
            error=error,
            bookmark=bookmark,
            title=title,
            url=url,
            tags=tags,
            comments=comments,
        ).pop()
