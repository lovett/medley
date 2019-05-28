"""Storage and search for bookmarked URLs."""

import re
from urllib.parse import urlparse
import cherrypy
import pendulum
from . import mixins
from . import decorators


class Plugin(cherrypy.process.plugins.SimplePlugin, mixins.Sqlite):
    """A CherryPy plugin for storing bookmarks."""

    def __init__(self, bus):
        cherrypy.process.plugins.SimplePlugin.__init__(self, bus)

        self.db_path = self._path("bookmarks.sqlite")

        self._create("""
        PRAGMA journal_mode=WAL;

        CREATE TABLE IF NOT EXISTS bookmarks (
            url,
            domain,
            added,
            added_date,
            updated DEFAULT NULL,
            retrieved DEFAULT NULL,
            deleted DEFAULT NULL,
            title DEFAULT NULL,
            tags DEFAULT NULL,
            comments DEFAULT NULL,
            fulltext DEFAULT NULL,
            UNIQUE(url)
        );

        CREATE VIRTUAL TABLE IF NOT EXISTS bookmarks_fts USING fts5(
            title,
            tags,
            comments,
            fulltext,
            content=bookmarks,
            tokenize=porter
        );

        CREATE INDEX IF NOT EXISTS bookmarks_added_date
            ON bookmarks (added_date);

        CREATE INDEX IF NOT EXISTS bookmarks_domain
            ON bookmarks (domain);

        CREATE INDEX IF NOT EXISTS bookmarks_fulltext_null
            ON bookmarks (fulltext)
            WHERE fulltext IS NULL;

        CREATE TRIGGER IF NOT EXISTS bookmarks_after_insert
        AFTER INSERT ON bookmarks
        BEGIN
        INSERT INTO bookmarks_fts (rowid, title, tags, comments, fulltext)
        VALUES (new.rowid, new.title, new.tags, new.comments, new.fulltext);
        END;

        CREATE TRIGGER IF NOT EXISTS bookmarks_after_update
        AFTER UPDATE OF fulltext ON bookmarks
        BEGIN
        INSERT INTO bookmarks_fts (bookmarks_fts, rowid, title, tags, comments,
            fulltext)
            VALUES ('delete', old.rowid, old.title, old.tags, old.comments,
            old.fulltext);
        INSERT INTO bookmarks_fts(rowid, title, tags, comments, fulltext)
            VALUES (new.rowid, new.title, new.tags, new.comments,
            new.fulltext);
        END;

        CREATE TRIGGER IF NOT EXISTS bookmarks_after_delete
        AFTER DELETE ON bookmarks
        BEGIN
        INSERT INTO bookmarks_fts(bookmarks_fts, rowid, title, tags, comments,
            fulltext)
            VALUES ('delete', old.rowid, old.title, old.tags, old.comments,
            old.fulltext);
        END;

        """)

    def start(self):
        """Define the CherryPy messages to listen for.

        This plugin owns the bookmarks prefix.

        It depends on the urlfetch plugin for URL retrieval.
        """

        self.bus.subscribe("server:ready", self.add_full_text)
        self.bus.subscribe("bookmarks:find", self.find)
        self.bus.subscribe("bookmarks:add", self.add)
        self.bus.subscribe("bookmarks:add:fulltext", self.add_full_text)
        self.bus.subscribe("bookmarks:search", self.search)
        self.bus.subscribe("bookmarks:generalize_query", self.generalize_query)
        self.bus.subscribe("bookmarks:recent", self.recent)
        self.bus.subscribe("bookmarks:remove", self.remove)
        self.bus.subscribe("bookmarks:repair", self.repair)

    @staticmethod
    def domain_and_url(url):
        """Parse the domain from a normalized URL."""

        parsed_url = urlparse(
            url.split('#', 1)[0],
            scheme='http',
            allow_fragments=False
        )

        return (
            parsed_url.netloc.lower(),
            parsed_url.geturl()
        )

    @staticmethod
    def generalize_query(query):
        """Convert a search query to a more generic form suitable for use with
        external search engines.

        """

        general_query = re.sub(r"(tag|comment)s?:", "", query)
        general_query = general_query.replace("domain:", "site:")
        return general_query

    def find(self, uid=None, url=None):
        """Locate a bookmark by ID or URL."""

        where_clause = None

        if uid:
            where_clause = "rowid=?"
            values = (uid,)

        if url:
            where_clause = "domain=? AND url=?"
            values = self.domain_and_url(url)

        if not where_clause:
            return False

        return self._selectOne(
            """SELECT rowid, url, domain, title,
            added as 'added [datetime]',
            updated as 'updated [datetime]',
            deleted as 'deleted [datetime]',
            tags, comments
            FROM bookmarks WHERE {}""".format(where_clause),  # nosec
            values
        )

    @decorators.log_runtime
    def add(self, url=None, title=None, comments=None, tags=None, added=None):
        """Store a bookmarked URL and its metadata."""

        bookmark = self.find(url=url)

        if bookmark:
            sql = """UPDATE bookmarks SET title=?, tags=?, comments=?,
            updated=CURRENT_TIMESTAMP, deleted=NULL WHERE rowid=?"""

            values = (
                title,
                tags,
                comments,
                bookmark["rowid"]
            )

            self._update(sql, [values])
            return True

        sql = """INSERT INTO bookmarks
        (domain, url, added, added_date, title, tags, comments)
        VALUES (?, ?, ?, ?, ?, ?, ?)"""

        domain_and_url = self.domain_and_url(url)

        if added and added.isnumeric():
            numeric_timestamp = int(added)
            add_date = pendulum.from_timestamp(numeric_timestamp)
        else:
            add_date = pendulum.now()

        values = (
            domain_and_url[0],
            domain_and_url[1],
            add_date.format('YYYY-MM-DD HH:mm:ss'),
            add_date.to_date_string(),
            title,
            tags,
            comments
        )

        self._insert(sql, [values])

        cherrypy.engine.publish(
            "scheduler:add",
            2,
            "bookmarks:add:fulltext"
        )

        return True

    @decorators.log_runtime
    def add_full_text(self):
        """Store the plain text of a bookmarked URL.

        This is only used for searching.
        """

        url = self._selectFirst("""SELECT url
        FROM bookmarks
        WHERE retrieved IS NULL
        LIMIT 1""")

        if not url:
            cherrypy.engine.publish(
                "applog:add",
                "bookmarks",
                "add_full_text",
                "0 unretrieved rows"
            )

            return

        html = cherrypy.engine.publish(
            "urlfetch:get",
            url
        ).pop()

        text = cherrypy.engine.publish(
            "markup:plaintext",
            html,
            url
        ).pop()

        self._insert(
            """UPDATE bookmarks
            SET fulltext=?, retrieved=CURRENT_TIMESTAMP
            WHERE url=?""",
            [(text, url)]
        )

        cherrypy.engine.publish(
            "scheduler:remove",
            "bookmarks:add:fulltext"
        )

        cherrypy.engine.publish(
            "scheduler:add",
            10,
            "bookmarks:add:fulltext"
        )

    @decorators.log_runtime
    def remove(self, url):
        """Discard a previously bookmarked URL."""

        return self._delete(
            "UPDATE bookmarks SET deleted=CURRENT_TIMESTAMP WHERE url=?",
            (url,)
        )

    @decorators.log_runtime
    def search(self, query, order="date-desc", limit=20, offset=0):
        """Locate bookmarks via fulltext search.

        Ranking is based on the built-in hidden rank column provided
        by Sqlite FTS5, which the Sqlite documentation indicates is
        faster than using the bm25() function and specifying custom
        weights for each column.

        In testing, there wasn't a huge difference between the two.

        """

        from_sql = "bookmarks b"
        where_sql = "b.deleted IS NULL"
        placeholder_values = ()
        order_sql = "b.added DESC"

        if "tag:" in query:
            query = query.replace("tag:", "tags:")

        if "comment:" in query:
            query = query.replace("comment:", "comments:")

        if "domain:" in query:
            match = re.search(r"domain:\s*(\S+)", query)
            if match:
                where_sql += " AND b.domain=?"
                placeholder_values += (match.group(1),)
                query = query.replace(match.group(0), "")

        if query:
            # The query is sanitized to prevent FTS5 syntax errors
            query = re.sub(r"[^\w ]", "_", query)

            # Semicolons are allowed after column names
            query = re.sub(r"\b(tags|comments|domain)_\s*", r"\g<1>:", query)

            from_sql = "bookmarks_fts, bookmarks b"
            where_sql += """ AND bookmarks_fts.rowid=b.rowid
            AND bookmarks_fts MATCH ?"""

            if order == "rank":
                order_sql = "bookmarks_fts.rank"
            if order == "date-asc":
                order_sql = "b.added ASC"

            placeholder_values += (query,)

        sql = """SELECT b.url, b.domain, b.title,
        b.comments, b.tags as 'tags [comma_delimited]',
        added as 'added [datetime]',
        updated as 'updated [datetime]'
        FROM {}
        WHERE {}
        ORDER BY {}
        LIMIT ? OFFSET ?""".format(  # nosec
            from_sql,
            where_sql,
            order_sql
        )

        placeholder_values += (limit, offset)

        return (
            self._select(sql, placeholder_values),
            self._count(sql, placeholder_values),
            self._explain(sql, placeholder_values)
        )

    @decorators.log_runtime
    def recent(self, limit=20, offset=0, max_days=180):
        """Get a newest-first list of recently bookmarked URLs."""

        sql = """SELECT url, domain, title,
        added as 'added [datetime]',
        updated as 'updated [datetime]',
        retrieved 'retrieved [datetime]',
        comments, tags as 'tags [comma_delimited]'
        FROM bookmarks
        WHERE added_date >= ?
        AND deleted IS NULL
        ORDER BY added DESC
        LIMIT ? OFFSET ?"""

        cutoff_date = pendulum.now().subtract(
            days=max_days
        ).to_date_string()

        return (
            self._select(sql, (cutoff_date, limit, offset)),
            self._count(sql, (cutoff_date,)),
            self._explain(sql, (cutoff_date, limit, offset))
        )

    def prune(self):
        """Delete rows that have been marked for removal.

        This is normally invoked from the maintenance plugin.

        """

        deletion_count = self._delete(
            "DELETE FROM bookmarks WHERE deleted IS NOT NULL"
        )

        cherrypy.engine.publish(
            "applog:add",
            "bookmarks",
            "prune",
            "pruned {} records".format(deletion_count)
        )

    @decorators.log_runtime
    def repair(self):
        """Correct wrong or missing values."""

        rows_without_domain = self._select_generator(
            "SELECT rowid, url FROM bookmarks WHERE domain IS NULL"
        )

        for row in rows_without_domain:
            (domain, _) = self.domain_and_url(row["url"])
            self._update(
                "UPDATE bookmarks SET domain=? WHERE rowid=?",
                [(domain, row["rowid"])]
            )
