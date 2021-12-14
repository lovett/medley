"""Bookmark a webpage"""

import re
import cherrypy
from pydantic import BaseModel
from pydantic import ValidationError
from pydantic import Field, HttpUrl
from resources.url import Url


class GetParams(BaseModel):
    """Parameters for GET requests."""
    url: HttpUrl = Field("")
    title: str = Field("", strip_whitespace=True)
    tags: str = Field("", strip_whitespace=True)
    comments: str = Field("", strip_whitespace=True)


class Controller:
    """Dispatch application requests based on HTTP verb."""

    exposed = True
    show_on_homepage = True

    @staticmethod
    @cherrypy.tools.provides(formats=("html",))
    def GET(**kwargs: str) -> bytes:
        """Display a form for for bookmarking a URL"""

        try:
            params = GetParams(**kwargs)
        except ValidationError as error:
            raise cherrypy.HTTPError(400) from error

        url = Url(params.url)

        if params.title:
            title = cherrypy.engine.publish(
                "markup:plaintext",
                params.title,
                url
            ).pop()

            title = cherrypy.engine.publish(
                "markup:reduce:title",
                title
            ).pop()

        if params.tags:
            params.tags = cherrypy.engine.publish(
                "markup:plaintext",
                params.tags
            ).pop()

        # Meta description tags on Reddit aren't specific to the URL
        # being bookmarked.
        if "reddit.com" in url.domain and params.comments.startswith("r/"):
            params.comments = ""

        if params.comments:
            params.comments = cherrypy.engine.publish(
                "markup:plaintext",
                params.comments
            ).pop()
            params.comments = re.sub(r"\s+", " ", params.comments).strip()
            params.comments = re.sub(r",(\w)", ", \\1", params.comments)
            params.comments = ". ".join([
                sentence[0].capitalize() + sentence[1:]
                for sentence in params.comments.split(". ")
            ])

            if not params.comments.endswith("."):
                params.comments += "."

        bookmark = None
        if url:
            bookmark = cherrypy.engine.publish(
                "bookmarks:find:url",
                url
            ).pop()

        if bookmark:
            params.title = bookmark["title"]
            params.tags = bookmark["tags"]
            params.comments = bookmark["comments"]

        bookmarks_url = cherrypy.engine.publish(
            "app_url",
            "/bookmarks",
            {"query": params.title, "order": "date-desc"}
        ).pop()

        return cherrypy.engine.publish(
            "jinja:render",
            "apps/later/later.jinja.html",
            bookmarks_url=bookmarks_url,
            bookmark=bookmark,
            title=params.title,
            url=url,
            tags=params.tags,
            comments=params.comments,
        ).pop()
