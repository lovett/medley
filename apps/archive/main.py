import cherrypy
import apps.archive.models
import tools
import pytz
from collections import OrderedDict
import util.net

class Controller:
    """A collection of bookmarked URLs"""

    name = "Archive"

    exposed = True

    user_facing = True

    dbconn = None

    @cherrypy.tools.template(template="archive.html")
    @cherrypy.tools.negotiable()
    def GET(self, date=None, q=None, action=None, bookmark_id=None):
        entries = OrderedDict()
        timezone = pytz.timezone(cherrypy.config.get("timezone"))
        archive = apps.archive.models.Archive()

        if not q:
            records = archive.recent(limit=50)
        else:
            records = archive.search(q)

        for record in records:
            key = record["created"].astimezone(timezone)
            key = key.strftime("%Y-%m-%d")

            if not key in entries:
                entries[key] = []

            entries[key].append(record)

        return {
            "app_name": self.name,
            "entries": entries,
            "q": q
        }

    def POST(self, url, title=None, tags=None, comments=None):
        archive = apps.archive.models.Archive()
        record = archive.find(url=url)

        if record:
            page = None
        else:
            page = archive.fetch(url)

        if page and not title:
            title = util.net.getHtmlTitle(page)
            title = archive.reduceHtmlTitle(title)

        url_id = archive.add(url, title, comments, tags)

        if page:
            text = util.net.htmlToText(page)
            archive.addFullText(url_id, text)

        cherrypy.response.status = 204



    def DELETE(self, uid):
        archive = apps.archive.models.Archive()
        record_count = archive.count(uid=uid)

        if record_count != 1:
            raise cherrypy.HTTPError(404, "Invalid id")

        removals = archive.remove(uid=uid)
