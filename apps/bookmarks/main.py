"""Manage a collection of bookmarked URLs."""

import cherrypy


class Controller:
    """Dispatch application requests based on HTTP verb."""

    name = "Bookmarks"

    @staticmethod
    def check_wayback_availability(url):
        """See if an archived copy of the URL is available."""

        response = cherrypy.engine.publish(
            "urlfetch:get",
            "http://archive.org/wayback/available",
            params={"url": url},
            as_json=True
        ).pop() or {}

        snapshots = response.get("archived_snapshots", {})
        closest_snapshot = snapshots.get("closest", {})
        return closest_snapshot

    @cherrypy.tools.negotiable()
    def GET(self, *args, **kwargs):
        """Display a list of recently bookmarked URLs, or URLs matching a
        search.

        """

        order = kwargs.get('order', 'rank')
        query = kwargs.get('query')
        page = int(kwargs.get('page', 1))
        per_page = 20
        offset = (page - 1) * per_page
        recent_tags = ()

        if query:
            query = query.strip()

        if args == ('taglist',):
            return self.taglist()

        if kwargs.get('wayback'):
            return {
                "json": self.check_wayback_availability(kwargs.get('wayback'))
            }

        if query:
            max_days = None
            (bookmarks, count, query_plan) = cherrypy.engine.publish(
                "bookmarks:search",
                query,
                order=order,
                limit=per_page,
                offset=offset,
            ).pop()
        else:
            max_days = 180
            (bookmarks, count, query_plan) = cherrypy.engine.publish(
                "bookmarks:recent",
                limit=per_page,
                offset=offset,
                max_days=max_days
            ).pop()

            recent_tags = cherrypy.engine.publish(
                "bookmarks:tags:recent",
                max_days=max_days
            ).pop()

        start_index = offset + 1
        end_index = offset + len(bookmarks)

        total_pages = count // per_page + 1

        next_page = page + 1
        if next_page > total_pages:
            next_page = None

        previous_page = page - 1
        if previous_page < 1:
            previous_page = None

        general_query = None
        if query:
            general_query = cherrypy.engine.publish(
                "bookmarks:generalize_query",
                query
            ).pop()

        return {
            "html": ("bookmarks.jinja.html", {
                "bookmarks": bookmarks,
                "recent_tags": recent_tags,
                "max_days": max_days,
                "count": count,
                "query": query,
                "general_query": general_query,
                "query_plan": query_plan,
                "order": order,
                "next_page": next_page,
                "previous_page": previous_page,
                "total_pages": total_pages,
                "page": page,
                "start_index": start_index,
                "end_index": end_index
            })
        }

    @staticmethod
    def POST(url, title=None, tags=None, comments=None, added=None):
        """Add a new bookmark, or update an existing one."""

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
    def DELETE(url):
        """Discard a previously bookmarked URL."""

        deleted_rows = cherrypy.engine.publish(
            "bookmarks:remove",
            url
        ).pop()

        if not deleted_rows:
            raise cherrypy.HTTPError(404, "Invalid url")

        cherrypy.response.status = 204

    @staticmethod
    def taglist():
        """Render a list of all known bookmark tags using a dedicated
        template.

        """

        tags = cherrypy.engine.publish(
            "bookmarks:tags:all"
        ).pop()

        return {
            "html": ("bookmarks-taglist.jinja.html", {
                "tags": tags,
            })
        }
