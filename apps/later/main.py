"""Display a form for bookmarking a URL."""

import re
import cherrypy


class Controller:
    """Dispatch application requests based on HTTP verb."""

    name = "Later"

    @cherrypy.tools.negotiable()
    def GET(self, *_args, **kwargs):
        """Display a form for for bookmarking a URL"""

        error = None
        url = kwargs.get('url')
        title = kwargs.get('title')
        tags = kwargs.get('tags')
        comments = kwargs.get('comments')

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

        # Discard comment if it came from a meta description tag on Reddit,
        # since it isn't specific to the URL being bookmarked.
        if comments and comments.startswith("r/") and "reddit.com" in url:
            comments = None

        if comments:
            comments = cherrypy.engine.publish(
                "markup:plaintext",
                comments
            ).pop()
            comments = re.sub(r"\s+", " ", comments).strip()
            comments = re.sub(r",(\w)", ", \\1", comments)
            comments = comments.split(". ")
            comments = ". ".join([
                sentence[0].capitalize() + sentence[1:]
                for sentence in comments
            ])

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

        bookmarks_url = cherrypy.engine.publish(
            "url:internal",
            "/bookmarks"
        ).pop()

        return {
            "html": ("later.jinja.html", {
                "bookmarks_url": bookmarks_url,
                "error": error,
                "bookmark": bookmark,
                "title": title,
                "url": url,
                "tags": tags,
                "comments": comments,
            })
        }
