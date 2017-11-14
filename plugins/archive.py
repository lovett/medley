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
        self.bus.subscribe("archive:add", self.add)
        self.bus.subscribe("archive:add_fulltext", self.addFullText)
        self.bus.subscribe("archive:count", self.count)
        self.bus.subscribe("archive:search", self.search)
        self.bus.subscribe("archive:recent", self.recent)
        self.bus.subscribe("archive:remove", self.remove)

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

    def add(self, url, title, comments=None, tags=None):
        parsed_url = urlparse(url)

        url_id = self._insert(
            "INSERT OR REPLACE INTO urls (url, domain) VALUES (?, ?)",
            (url, parsed_url.netloc)
        )

        self._insert(
            """INSERT OR REPLACE INTO meta (url_id, title, comments, tags)
            VALUES (?, ?, ?, ?)""",
            (url_id, title, comments, tags)
        )
        return url_id

    def addFullText(self, url_id, fulltext):
        rowid = self._insert(
            "UPDATE meta SET fulltext=? WHERE url_id=?",
            (fulltext, url_id)
        )
        return rowid

    def remove(self, uid):
        rowcount = self._delete("DELETE FROM urls WHERE rowid=?", (int(uid),))
        self._delete("DELETE FROM meta WHERE url_id=?", (int(uid),))
        return rowcount

    def count(self, uid):
        sql = """SELECT count(*) as total FROM urls WHERE rowid=?"""
        result = self._selectOne(sql, (int(uid),))
        return result["total"]

    def search(self, search):
        sql = """SELECT u.rowid, u.url, u.domain, m.title,
            u.created as 'created [created]', m.tags, m.comments
            FROM urls u, meta m WHERE u.rowid=m.url_id AND meta MATCH ?
            ORDER BY u.created DESC"""
        return self._select(sql, (search,))

    def recent(self, limit=100):
        sql = """SELECT u.rowid, u.url, u.domain, m.title, case when m.fulltext is
        null then 0 else 1 end as has_fulltext, u.created as 'created [created]', m.tags, m.comments, 'bookmark' as record_type FROM urls u, meta m WHERE u.rowid=m.url_id ORDER BY u.created DESC LIMIT ?"""
        return self._select(sql, (limit,))
