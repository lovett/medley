"""Manage a collection of bookmarked URLs."""

import cherrypy
import pytz
from urllib.parse import urlparse
from collections import OrderedDict

class Controller:
    """Dispatch application requests based on HTTP verb."""

    name = "Archive"

    exposed = True

    user_facing = True

    def checkWaybackAvailability(self, url):
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
    def GET(self, date=None, q=None, action=None, bookmark_id=None, wayback=None):
        entries = OrderedDict()

        if wayback:
            return {
                "json": self.checkWaybackAvailability(wayback)
            }

        if not q:
            records = cherrypy.engine.publish("archive:recent", limit=50).pop()
        else:
            records = cherrypy.engine.publish("archive:search", q).pop()

        for record in records:
            key = record["created"].strftime("%Y-%m-%d")

            if not key in entries:
                entries[key] = []

            entries[key].append(record)

        return {
            "html": ("archive.html", {
                "app_name": self.name,
                "entries": entries,
                "q": q
            })
        }

    def POST(self, url, title=None, tags=None, comments=None):
        parsed_url = urlparse(url.lower())

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

    def DELETE(self, uid):
        deletion_count = cherrypy.engine.publish(
            "archive:remove", uid
        ).pop()

        if deletion_count != 1:
            raise cherrypy.HTTPError(404, "Invalid id")

        cherrypy.response.status = 204
