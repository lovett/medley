"""Store bookmarked URLs."""

import cherrypy
from . import mixins


class Plugin(cherrypy.process.plugins.SimplePlugin, mixins.Sqlite):
    """A CherryPy plugin for storing bookmarked URLs."""

    def __init__(self, bus):
        cherrypy.process.plugins.SimplePlugin.__init__(self, bus)

        self.db_path = self._path("archive.sqlite")

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
        """Define the CherryPy messages to listen for.

        This plugin owns the archive prefix.
        """
        self.bus.subscribe("archive:find", self.find)
        self.bus.subscribe("archive:add", self.add)
        self.bus.subscribe("archive:add_fulltext", self.add_full_text)
        self.bus.subscribe("archive:count", self.count)
        self.bus.subscribe("archive:search", self.search)
        self.bus.subscribe("archive:recent", self.recent)
        self.bus.subscribe("archive:remove", self.remove)

    def find(self, uid=None, url=None):
        """Locate a record by a unique identifier"""

        sql = """SELECT u.rowid, u.url, u.domain, m.title,
            u.created as 'created [datetime]', m.tags, m.comments
            FROM urls u, meta m WHERE u.rowid=m.url_id"""

        if uid:
            sql += " AND u.rowid=?"
            params = (uid, )

        if url:
            sql += " AND u.url=?"
            params = (url.lower(),)

        return self._selectOne(sql, params)

    def add(self, parsed_url, title=None, comments=None, tags=None):
        """Store a bookmarked URL and its metadata."""

        self._multi((
            ("""INSERT OR IGNORE INTO urls
            (url, domain) VALUES (?, ?)""",
             (parsed_url.geturl(), parsed_url.netloc)),
            ("""UPDATE meta SET title=?, comments=?, tags=?
            WHERE url_id=(SELECT rowid
            FROM urls WHERE url=?)""",
             (title, comments, tags, parsed_url.geturl())),
            ("""INSERT INTO meta (url_id, title, comments, tags)
            SELECT last_insert_rowid(), ?, ?, ?
            WHERE (SELECT Changes() = 0)""",
             (title, comments, tags)),
        ))

        return True

    def add_full_text(self, url_id, fulltext):
        """Store the source markup of a bookmarked URL."""

        return self._insert(
            "UPDATE meta SET fulltext=? WHERE url_id=?",
            [(fulltext, url_id)]
        )

    def remove(self, uid):
        """Discard a bookmarked URL."""

        rowcount = self._delete("DELETE FROM urls WHERE rowid=?", (int(uid),))
        self._delete("DELETE FROM meta WHERE url_id=?", (int(uid),))
        return rowcount

    def count(self, uid):
        """Test whether a URL has already been bookmarked."""

        sql = """SELECT count(*) as total FROM urls WHERE rowid=?"""
        result = self._selectOne(sql, (int(uid),))
        return result["total"]

    def search(self, search, limit=50):
        """Search for bookmarks by fulltext keyword."""

        sql = """SELECT u.rowid, u.url, u.domain, m.title,
            u.created as 'created [datetime]', m.tags, m.comments
            FROM urls u, meta m WHERE u.rowid=m.url_id AND meta MATCH ?
            ORDER BY u.created DESC LIMIT ?"""
        return self._select(sql, (search, limit))

    def recent(self, limit=50):
        """Get a newest-first list of recently bookmarked URLs."""

        sql = """SELECT u.rowid, u.url, u.domain, m.title,
        CASE WHEN m.fulltext is null then 0
        else 1
        end as has_fulltext,
        u.created as 'created [datetime]',
        m.tags, m.comments, 'bookmark' as record_type
        FROM urls u, meta m
        WHERE u.rowid=m.url_id
        ORDER BY u.created DESC
        LIMIT ?"""

        return self._select(sql, (limit,))
