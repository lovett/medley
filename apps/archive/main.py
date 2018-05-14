"""Manage a collection of bookmarked URLs."""

from urllib.parse import urlparse
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
        """Accept a bookmark URL for storage."""

        parsed_url = urlparse(url)

        if not parsed_url.netloc:
            raise cherrypy.HTTPError(400, "Invalid URL")

        cherrypy.engine.publish(
            "archive:add",
            parsed_url,
            title,
            comments,
            tags
        )

        cherrypy.response.status = 204

    @staticmethod
    def DELETE(uid):
        """Remove a previously bookmarked URL from storage."""

        deletion_count = cherrypy.engine.publish(
            "archive:remove", uid
        ).pop()

        if deletion_count != 1:
            raise cherrypy.HTTPError(404, "Invalid id")

        cherrypy.response.status = 204
