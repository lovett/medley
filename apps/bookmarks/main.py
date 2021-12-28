"""Saved webpages"""

from enum import Enum
import json
import sqlite3
import typing
from pydantic import BaseModel
from pydantic import Field
from pydantic import ValidationError
import cherrypy
from resources.url import Url


class Subresource(str, Enum):
    """Valid keywords for the first URL path segment of this application."""
    NONE = ""
    TAGLIST = "taglist"


class GetParams(BaseModel):
    """Parameters for GET requests."""
    subresource: Subresource = Subresource.NONE
    q: str = Field("", strip_whitespace=True, min_length=1)
    wayback: str = Field("", strip_whitespace=True, min_length=1)
    offset: int = 0
    max_days: int = 180
    per_page: int = 20
    order: str = Field("rank", strip_whitespace=True, min_length=1)


class DeleteParams(BaseModel):
    """Parameters for DELETE requests."""
    uid: int = Field(0, gt=0)


class Controller:
    """Dispatch application requests based on HTTP verb."""

    exposed = True
    show_on_homepage = True

    @staticmethod
    def DELETE(uid: int) -> None:
        """Discard a previously bookmarked URL."""

        try:
            params = DeleteParams(uid=uid)
        except ValidationError as error:
            raise cherrypy.HTTPError(400) from error

        deleted_rows = cherrypy.engine.publish(
            "bookmarks:remove",
            params.uid
        ).pop()

        if not deleted_rows:
            raise cherrypy.HTTPError(404, "Invalid url")

        cherrypy.response.status = 204

    @cherrypy.tools.provides(formats=("json", "html"))
    def GET(self, subresource: str = "", **kwargs: str) -> bytes:
        """Dispatch to a subhandler based on the URL path."""

        try:
            params = GetParams(
                subresource=subresource,
                **kwargs
            )
        except ValidationError as error:
            raise cherrypy.HTTPError(400) from error

        if params.q:
            return self.search(params)

        if params.wayback:
            return self.check_wayback_availability(params)

        if params.subresource == Subresource.TAGLIST:
            return self.taglist()

        return self.index(params)

    @staticmethod
    def POST(url: str, **kwargs: str) -> None:
        """Add a new bookmark, or update an existing one."""

        title = kwargs.get("title")
        tags = kwargs.get("tags")
        comments = kwargs.get("comments")
        added = kwargs.get("added")

        result = cherrypy.engine.publish(
            "scheduler:add",
            2,
            "bookmarks:add",
            Url(url),
            title,
            comments,
            tags,
            added
        ).pop()

        if not result:
            raise cherrypy.HTTPError(400)

        cherrypy.response.status = 204

    @staticmethod
    def check_wayback_availability(params: GetParams) -> bytes:
        """See if an archived copy of the URL is available."""

        response = cherrypy.engine.publish(
            "urlfetch:get:json",
            "http://archive.org/wayback/available",
            params={"url": params.wayback},
            cache_lifespan=86400
        ).pop() or {}

        snapshots = response.get("archived_snapshots", {})
        closest_snapshot = snapshots.get("closest", {})
        return json.dumps(closest_snapshot).encode()

    @staticmethod
    def count_by_domain(
            bookmarks: typing.Iterator[sqlite3.Row]
    ) -> typing.Dict[str, int]:
        """ Get bookmark counts per domain for a set of bookmarks."""
        counts = {}

        for bookmark in bookmarks:
            key = bookmark["url"].display_domain
            if key not in counts:
                counts[key] = cherrypy.engine.publish(
                    "bookmarks:domaincount",
                    bookmark["url"]
                ).pop()

        return counts

    def index(self, params: GetParams) -> bytes:
        """Display recently-added bookmarks."""

        (bookmarks, total_records, query_plan) = cherrypy.engine.publish(
            "bookmarks:recent",
            limit=params.per_page,
            offset=params.offset,
            max_days=params.max_days
        ).pop()

        domain_counts = self.count_by_domain(bookmarks)

        pagination_url = cherrypy.engine.publish(
            "app_url",
            "/bookmarks",
        ).pop()

        return cherrypy.engine.publish(
            "jinja:render",
            "apps/bookmarks/bookmarks.jinja.html",
            bookmarks=bookmarks,
            domain_counts=domain_counts,
            max_days=params.max_days,
            total_records=total_records,
            order=params.order,
            per_page=params.per_page,
            query_plan=query_plan,
            offset=params.offset,
            pagination_url=pagination_url
        ).pop()

    def search(self, params: GetParams) -> bytes:
        """Find bookmarks matching a search query."""

        (bookmarks, total_records, query_plan) = cherrypy.engine.publish(
            "bookmarks:search",
            params.q,
            limit=params.per_page,
            offset=params.offset,
            order=params.order
        ).pop()

        domain_counts = {}
        if "site:" not in params.q:
            domain_counts = self.count_by_domain(bookmarks)

        pagination_url = cherrypy.engine.publish(
            "app_url",
            "/bookmarks",
            {
                "q": params.q,
                "order": params.order
            }
        ).pop()

        return cherrypy.engine.publish(
            "jinja:render",
            "apps/bookmarks/bookmarks.jinja.html",
            bookmarks=bookmarks,
            domain_counts=domain_counts,
            offset=params.offset,
            order=params.order,
            pagination_url=pagination_url,
            per_page=params.per_page,
            q=params.q,
            query_plan=query_plan,
            total_records=total_records,
            subview_title=params.q
        ).pop()

    @staticmethod
    def taglist() -> bytes:
        """List all known bookmark tags."""

        tags = cherrypy.engine.publish(
            "bookmarks:tags:all"
        ).pop()

        return cherrypy.engine.publish(
            "jinja:render",
            "apps/bookmarks/bookmarks-taglist.jinja.html",
            tags=tags,
            subview_title="Tags"
        ).pop()
