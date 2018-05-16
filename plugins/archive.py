"""Storage and search for bookmarked URLs."""

import cherrypy
from urllib.parse import urlparse
from . import mixins
from . import decorators


class Plugin(cherrypy.process.plugins.SimplePlugin, mixins.Sqlite):
    """A CherryPy plugin for storing bookmarks."""

    def __init__(self, bus):
        cherrypy.process.plugins.SimplePlugin.__init__(self, bus)

        self.db_path = self._path("bookmarks.sqlite")

        # Because this is a virtual table, the added field can't
        self._create("""
        CREATE VIRTUAL TABLE IF NOT EXISTS bookmarks USING fts4 (
            url,
            domain,
            added,
            retrieved,
            title,
            tags,
            comments,
            fulltext,
            tokenize=porter,
            notindexed=added,
            notindexed=retrieved,
            order=desc
        );
        """)

    def start(self):
        """Define the CherryPy messages to listen for.

        This plugin owns the archive prefix.
        """
        self.bus.subscribe("archive:find", self.find)
        self.bus.subscribe("archive:add", self.add)
        self.bus.subscribe("archive:add:fulltext", self.add_full_text)
        self.bus.subscribe("archive:search", self.search)
        self.bus.subscribe("archive:recent", self.recent)
        self.bus.subscribe("archive:remove", self.remove)

    def find(self, uid=None, url=None):
        """Locate a bookmark by ID or URL."""

        where_clause = None

        if uid:
            where_clause = "rowid=?"
            values = (uid,)

        if url:
            where_clause = "url MATCH ?"
            values = (url,)

        if not where_clause:
            return False

        return self._selectOne(
            """SELECT rowid, url, domain, title,
            added as 'added [datetime]', tags, comments
            FROM bookmarks WHERE 1=1 AND {}""".format(where_clause),
            values
        )

    @decorators.log_runtime
    def add(self, url=None, title=None, comments=None, tags=None):
        """Store a bookmarked URL and its metadata."""

        parsed_url = urlparse(
            url.split('#', 1)[0],
            scheme='http',
            allow_fragments=False
        )

        if not parsed_url.netloc:
            return False

        bookmark_id = self._selectFirst(
            "SELECT rowid FROM bookmarks WHERE url MATCH ?",
            (parsed_url.geturl(),)
        )

        if bookmark_id:
            sql = """UPDATE bookmarks
            SET title=?, tags=?, comments=?
            WHERE rowid=?"""

            values = (
                title,
                tags,
                comments,
                bookmark_id
            )
        else:
            sql = """INSERT INTO bookmarks
            (url, domain, added, title, tags, comments)
            VALUES (?, ?, CURRENT_TIMESTAMP, ?, ?, ?)"""

            values = (
                parsed_url.geturl(),
                parsed_url.netloc.lower(),
                title,
                tags,
                comments
            )

        self._insert(sql, [values])

        cherrypy.engine.publish(
            "scheduler:add",
            2,
            "archive:add:fulltext",
            parsed_url.geturl(),
        )

        return True

    @decorators.log_runtime
    def add_full_text(self, url):
        """Store the source markup of a bookmarked URL."""

        html = cherrypy.engine.publish(
            "urlfetch:get",
            url
        ).pop()

        text = cherrypy.engine.publish(
            "markup:plaintext",
            html
        ).pop()

        self._insert(
            """UPDATE bookmarks
            SET fulltext=?, retrieved=CURRENT_TIMESTAMP
            WHERE url=?""",
            [(text, url)]
        )

    @decorators.log_runtime
    def remove(self, url):
        """Discard a previously bookmarked URL."""

        return self._delete(
            "DELETE FROM bookmarks WHERE url=?",
            (url,)
        )

    @decorators.log_runtime
    def search(self, query, limit=20, offset=0):
        """Locate bookmarks via fulltext search.

        Ranking is based on term frequency.
        """

        # How much value to give matches from each column of the
        # virtual table, in the order they appear in the create table
        # statement. Includes non-indexed fields.
        weights = (
            0.00,   # url
            0.25,   # domain
            -1.00,  # added (not indexed)
            -1.00,  # retrieved (not indexed)
            0.75,   # title
            0.80,   # tags
            0.50,   # comments
            0.60    # fulltext
        )

        weight_string = ",".join(map(repr, weights))

        return self._fts_search(
            """SELECT url, domain, title,
            added as 'added [datetime]', rank
            FROM bookmarks JOIN (
                SELECT docid, rank(matchinfo(bookmarks, 'pcx'), {}) as rank
                FROM bookmarks
                WHERE bookmarks MATCH ?
                ORDER BY rank DESC
                LIMIT ? OFFSET ?
            ) as ranktable USING(docid)
            ORDER BY ranktable.rank DESC""".format(weight_string),
            (query, limit, offset)
        )

    @decorators.log_runtime
    def recent(self, limit=20):
        """Get a newest-first list of recently bookmarked URLs."""

        sql = """SELECT url, domain, title,
        added as 'added [datetime]',
        retrieved 'retrieved [datetime]',
        tags, comments
        FROM bookmarks
        ORDER BY rowid DESC
        LIMIT ?"""

        return self._select(sql, (limit,))
