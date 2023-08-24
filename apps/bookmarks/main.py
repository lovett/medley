"""Saved webpages"""

import json
import sqlite3
from typing import Dict
from typing import Iterator
import cherrypy
from resources.url import Url


class Controller:
    exposed = True
    show_on_homepage = True

    @staticmethod
    def DELETE(uid: str) -> None:
        """Discard a previously bookmarked URL."""

        try:
            record_id = int(uid)
        except ValueError as exc:
            raise cherrypy.HTTPError(400, "Invalid uid") from ecx

        deleted_rows = cherrypy.engine.publish(
            "bookmarks:remove",
            record_id
        ).pop()

        if not deleted_rows:
            raise cherrypy.HTTPError(404, "Invalid url")

        cherrypy.response.status = 204

    @cherrypy.tools.provides(formats=("html", "json"))
    def GET(self, subresource: str = "", **kwargs: str) -> bytes:
        """Dispatch to a subhandler based on the URL path."""

        q = kwargs.get("q", "")
        wayback = kwargs.get("wayback", "")
        offset = int(kwargs.get("offset", 0))
        max_days = int(kwargs.get("max_days", 180))
        per_page = int(kwargs.get("per_page", 20))
        order = kwargs.get("order", "rank")

        if q:
            return self.search(q, per_page, offset, order)

        if wayback:
            return self.check_wayback_availability(wayback)

        if subresource == "taglist":
            return self.taglist()

        return self.index(per_page, offset, order, max_days)

    @staticmethod
    def POST(url: str, **kwargs: str) -> None:
        """Add a new bookmark, or update an existing one."""

        title = kwargs.get("title", "")
        tags = kwargs.get("tags", "")
        comments = kwargs.get("comments", "")
        added = kwargs.get("added", "")

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
    def check_wayback_availability(wayback: str) -> bytes:
        """See if an archived copy of the URL is available."""

        response = cherrypy.engine.publish(
            "urlfetch:get:json",
            "http://archive.org/wayback/available",
            params={"url": wayback},
            cache_lifespan=86400
        ).pop() or {}

        snapshots = response.get("archived_snapshots", {})
        closest_snapshot = snapshots.get("closest", {})
        return json.dumps(closest_snapshot).encode()

    @staticmethod
    def count_by_domain(
            bookmarks: Iterator[sqlite3.Row]
    ) -> Dict[str, int]:
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

    def index(
            self,
            per_page: int,
            offset: int,
            order: str,
            max_days: int
    ) -> bytes:
        """Display recently-added bookmarks."""

        (bookmarks, total_records, query_plan) = cherrypy.engine.publish(
            "bookmarks:recent",
            limit=per_page,
            offset=offset,
            max_days=max_days
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
            max_days=max_days,
            total_records=total_records,
            order=order,
            per_page=per_page,
            query_plan=query_plan,
            offset=offset,
            pagination_url=pagination_url
        ).pop()

    def search(self, q: str, per_page: int, offset: int, order: str) -> bytes:
        """Find bookmarks matching a search query."""

        (bookmarks, total_records, query_plan) = cherrypy.engine.publish(
            "bookmarks:search",
            q,
            limit=per_page,
            offset=offset,
            order=order
        ).pop()

        domain_counts = {}
        if "site:" not in q:
            domain_counts = self.count_by_domain(bookmarks)

        pagination_url = cherrypy.engine.publish(
            "app_url",
            "/bookmarks",
            {
                "q": q,
                "order": order
            }
        ).pop()

        return cherrypy.engine.publish(
            "jinja:render",
            "apps/bookmarks/bookmarks.jinja.html",
            bookmarks=bookmarks,
            domain_counts=domain_counts,
            offset=offset,
            order=order,
            pagination_url=pagination_url,
            per_page=per_page,
            q=q,
            query_plan=query_plan,
            total_records=total_records,
            subview_title=q
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
