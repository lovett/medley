import cherrypy
import pytz
from collections import OrderedDict

class Controller:
    """A collection of bookmarked URLs"""

    url = "/archive"

    name = "Archive"

    exposed = True

    user_facing = True

    @cherrypy.tools.negotiable()
    def GET(self, date=None, q=None, action=None, bookmark_id=None):
        entries = OrderedDict()
        timezone = pytz.timezone(cherrypy.config.get("timezone"))

        if not q:
            records = cherrypy.engine.publish("archive:recent", limit=50).pop()
        else:
            records = cherrypy.engine.publish("archive:search", q).pop()

        for record in records:
            key = record["created"].astimezone(timezone)
            key = key.strftime("%Y-%m-%d")

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
        record = archive.find(url=url)

        if record:
            page = None
        else:
            page = cherrypy.engine.publish(
                "urlfetch:get",
                url
            )

        if page and not title:
            title = cherrypy.engine.publish(
                "markup:html_title",
                page,
                with_reduce=true
            ).pop()

        url_id = cherrypy.engine.publish(
            "archive:add",
            url,
            title,
            comments,
            tags
        ).pop()

        if page:
            text = cherrypy.engine.publish(
                "markup:html_to_text", page
            ).pop()

            cherrypy.engine.publish(
                "add_fulltext",
                url_id,
                text
            )

        cherrypy.response.status = 204

    def DELETE(self, uid):
        deletion_count = cherrypy.engine.publish(
            "archive:remove", uid
        ).pop()

        if deletion_count != 1:
            raise cherrypy.HTTPError(404, "Invalid id")

        cherrypy.response.status = 204
