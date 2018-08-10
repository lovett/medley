"""Display a form for bookmarking a URL."""

import re
import cherrypy


class Controller:
    """Dispatch application requests based on HTTP verb."""

    name = "Later"

    @cherrypy.tools.negotiable()
    def GET(self, url=None, title=None, tags=None, comments=None):
        """Display a form for for bookmarking a URL"""

        error = None

        if title:
            title = cherrypy.engine.publish(
                "markup:plaintext",
                title,
                url
            ).pop()

            title = cherrypy.engine.publish(
                "markup:reduce_title",
                title
            ).pop()

        if tags:
            tags = cherrypy.engine.publish(
                "markup:plaintext", tags
            ).pop()

        if comments:
            comments = cherrypy.engine.publish(
                "markup:plaintext",
                comments
            ).pop()
            comments = re.sub(r"\s+", " ", comments).strip()
            comments = re.sub(r",(\w)", ", \\1", comments)
            comments = comments.capitalize()

        # Discard comment if it came from a meta description tag on Reddit,
        # since it isn't specific to the URL being bookmarked.
        if comments.startswith("r/") and "reddit.com" in url:
            comments = ""

        if comments and not comments.endswith("."):
            comments += "."

        bookmark = None
        if url:
            bookmark = cherrypy.engine.publish(
                "bookmarks:find",
                url=url
            ).pop()

        if bookmark:
            title = bookmark["title"]
            tags = bookmark["tags"]
            comments = bookmark["comments"]

        app_url = cherrypy.engine.publish(
            "url:internal"
        ).pop()

        return {
            "html": ("later.jinja.html", {
                "app_url": app_url,
                "error": error,
                "bookmark": bookmark,
                "title": title,
                "url": url,
                "tags": tags,
                "comments": comments,
                "app_name": self.name
            })
        }
