"""Manage a collection of bookmarked URLs."""

import cherrypy


class Controller:
    """Dispatch application requests based on HTTP verb."""

    name = "Archive"

    @staticmethod
    def check_wayback_availability(url):
        """See if an archived copy of the URL is available."""

        response = cherrypy.engine.publish(
            "urlfetch:get",
            "http://archive.org/wayback/available",
            params={"url": url},
            as_json=True
        ).pop()

        snapshots = response.get("archived_snapshots", {})
        closest_snapshot = snapshots.get("closest", {})
        return closest_snapshot

    @cherrypy.tools.negotiable()
    def GET(self, query=None, wayback=None):
        """Display a list of recently bookmarked URLs, or URLs matching a
        search.

        """
        if wayback:
            return {
                "json": self.check_wayback_availability(wayback)
            }

        if query:
            bookmarks = cherrypy.engine.publish("archive:search", query).pop()
        else:
            bookmarks = cherrypy.engine.publish("archive:recent").pop()

        return {
            "html": ("archive.html", {
                "app_name": self.name,
                "bookmarks": bookmarks,
                "query": query
            })
        }

    @staticmethod
    def POST(url, title=None, tags=None, comments=None):
        """Add a new bookmark, or update an existing one."""

        result = cherrypy.engine.publish(
            "scheduler:add",
            2,
            "archive:add",
            url,
            title,
            comments,
            tags
        ).pop()

        if not result:
            raise cherrypy.HTTPError(400)

        cherrypy.response.status = 204

    @staticmethod
    def DELETE(url):
        """Discard a previously bookmarked URL."""

        deleted_rows = cherrypy.engine.publish(
            "archive:remove",
            url
        ).pop()

        if not deleted_rows:
            raise cherrypy.HTTPError(404, "Invalid id")

        cherrypy.response.status = 204
