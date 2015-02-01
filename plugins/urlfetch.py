import cherrypy
import util.net
import util.db
from cherrypy.process import wspbus, plugins

class Plugin(plugins.SimplePlugin):

    def __init(self, bus):
        plugins.SimplePlugin.__init__(self, bus)


    def start(self):
        """Called when the engine starts"""
        self.bus.log("Starting urlfetch")
        self.bus.subscribe("bookmark-fetch", self.fetchBookmark)

    def stop(self):
        """Called when the engine stops"""
        self.bus.log("Stopping urlfetch")
        self.bus.unsubscribe("bookmark-fetch", self.fetchBookmark)

    def fetchBookmark(self, url_id):
        """Fetch a URL"""
        bookmark = util.db.getBookmarkById(url_id)
        doc = util.net.getUrl(bookmark["url"])
        text = util.net.htmlToText(doc)
        util.db.saveBookmarkFulltext(url_id, text)
