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
    def GET(self, *_args, **kwargs):
        """Display a list of recently bookmarked URLs, or URLs matching a
        search.

        """

        query = kwargs.get('query')
        wayback = kwargs.get('wayback')

        if wayback:
            return {
                "json": self.check_wayback_availability(wayback)
            }

        if query:
            bookmarks = cherrypy.engine.publish(
                "bookmarks:search", query
            ).pop()
        else:
            bookmarks = cherrypy.engine.publish(
                "bookmarks:recent"
            ).pop()

        app_url = cherrypy.engine.publish("url:internal").pop()

        return {
            "html": ("bookmarks.jinja.html", {
                "app_name": self.name,
                "app_url": app_url,
                "bookmarks": bookmarks,
                "query": query
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
