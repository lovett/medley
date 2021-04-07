"""Saved webpages"""

import json
import sqlite3
import typing
import cherrypy


class Controller:
    """Dispatch application requests based on HTTP verb."""

    exposed = True
    show_on_homepage = True

    @staticmethod
    def DELETE(url: str) -> None:
        """Discard a previously bookmarked URL."""

        deleted_rows = cherrypy.engine.publish(
            "bookmarks:remove",
            url
            ).pop()

        if not deleted_rows:
            raise cherrypy.HTTPError(404, "Invalid url")

        cherrypy.response.status = 204

    @cherrypy.tools.provides(formats=("json", "html"))
    def GET(self, *args: str, **kwargs: str) -> bytes:
        """Dispatch to a subhandler based on the URL path."""

        if "query" in kwargs:
            return self.search(**kwargs)

        if "wayback" in kwargs:
            return self.check_wayback_availability(
                kwargs.get("wayback", "")
            )

        if args and args[0] == "taglist":
            return self.taglist()

        return self.index(**kwargs)

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
            url,
            title,
            comments,
            tags,
            added
        ).pop()

        if not result:
            raise cherrypy.HTTPError(400)

        cherrypy.response.status = 204

    @staticmethod
    def check_wayback_availability(url: str) -> bytes:
        """See if an archived copy of the URL is available."""

        response = cherrypy.engine.publish(
            "urlfetch:get",
            "http://archive.org/wayback/available",
            params={"url": url},
            as_json=True,
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
            domain = bookmark["domain"]
            if domain not in counts:
                counts[domain] = cherrypy.engine.publish(
                    "bookmarks:domaincount",
                    domain
                ).pop()
        return counts

    def index(self, *_args: str, **kwargs: str) -> bytes:
        """Display recently-added bookmarks."""

        max_days = 180
        per_page = 20
        offset = int(kwargs.get("offset", 0))
        order = "rank"

        (bookmarks, total_records, query_plan) = cherrypy.engine.publish(
            "bookmarks:recent",
            limit=per_page,
            offset=offset,
            max_days=max_days
        ).pop()

        domain_counts = self.count_by_domain(bookmarks)

        pagination_url = cherrypy.engine.publish(
            "url:internal",
            "/bookmarks",
        ).pop()

        return typing.cast(
            bytes,
            cherrypy.engine.publish(
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
        )

    def search(self, **kwargs: str) -> bytes:
        """Find bookmarks matching a search query."""
        per_page = 20
        offset = int(kwargs.get("offset", 0))
        query = kwargs.get("query", "").strip()
        order = kwargs.get("order", "rank")

        (bookmarks, total_records, query_plan) = cherrypy.engine.publish(
            "bookmarks:search",
            query,
            limit=per_page,
            offset=offset,
            order=order
        ).pop()

        domain_counts = {}
        if "domain:" not in query:
            domain_counts = self.count_by_domain(bookmarks)

        pagination_url = cherrypy.engine.publish(
            "url:internal",
            "/bookmarks",
            {
                "query": query,
                "order": order
            }
        ).pop()

        return typing.cast(
            bytes,
            cherrypy.engine.publish(
                "jinja:render",
                "apps/bookmarks/bookmarks.jinja.html",
                bookmarks=bookmarks,
                domain_counts=domain_counts,
                offset=offset,
                order=order,
                pagination_url=pagination_url,
                per_page=per_page,
                query=query,
                query_plan=query_plan,
                total_records=total_records,
                subview_title=query
            ).pop()
        )

    @staticmethod
    def taglist() -> bytes:
        """List all known bookmark tags."""

        tags = cherrypy.engine.publish(
            "bookmarks:tags:all"
        ).pop()

        return typing.cast(
            bytes,
            cherrypy.engine.publish(
                "jinja:render",
                "apps/bookmarks/bookmarks-taglist.jinja.html",
                tags=tags,
                subview_title="Tags"
            ).pop()
        )
