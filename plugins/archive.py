import cherrypy
from . import mixins

class Plugin(cherrypy.process.plugins.SimplePlugin, mixins.Sqlite):

    def __init__(self, bus):
        cherrypy.process.plugins.SimplePlugin.__init__(self, bus)

        self.db_path = self._path("archive.sqlite")

        self._registerConverters()

        self._create("""
        CREATE TABLE IF NOT EXISTS urls (
            url UNIQUE,
            created DEFAULT CURRENT_TIMESTAMP,
            domain
        );

        CREATE VIRTUAL TABLE IF NOT EXISTS meta USING fts4 (
            url_id, title, tags, comments,
            fulltext, tokenize=porter
        );

        CREATE INDEX IF NOT EXISTS url_domain ON urls (domain);
        """)

    def start(self):
        self.bus.subscribe("archive:find", self.find)

    def stop(self):
        pass

    def find(self, uid=None, url=None):
        """Locate a record by a unique identifier"""

        sql = """SELECT u.rowid, u.url, u.domain, m.title,
            u.created as 'created [created]', m.tags, m.comments
            FROM urls u, meta m WHERE u.rowid=m.url_id"""

        if uid:
            sql += " AND u.rowid=?"
            placeholders = (uid, )

        if url:
            sql += " AND u.url=?"
            placeholders = (url.lower(),)

        return self._selectOne(sql, params)
