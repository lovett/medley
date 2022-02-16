"""Storage and search for bookmarked URLs."""

import re
import sqlite3
from typing import Optional
from typing import List
from typing import Set
from typing import Tuple
from typing import Union
import cherrypy
from plugins import mixins
from plugins import decorators
from resources.url import Url


class Plugin(cherrypy.process.plugins.SimplePlugin, mixins.Sqlite):
    """A CherryPy plugin for storing bookmarks."""

    def __init__(self, bus: cherrypy.process.wspbus.Bus) -> None:
        cherrypy.process.plugins.SimplePlugin.__init__(self, bus)

        self.db_path = self._path("bookmarks.sqlite")

    def setup(self) -> None:
        """Create the database."""

        self._create("""
        PRAGMA journal_mode=WAL;

        CREATE TABLE IF NOT EXISTS bookmarks (
            url,
            domain,
            added,
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
            ON bookmarks (substr(added, 0, 11));

        CREATE INDEX IF NOT EXISTS bookmarks_domain
            ON bookmarks (domain);

        CREATE INDEX IF NOT EXISTS bookmarks_fulltext_null
            ON bookmarks (fulltext)
            WHERE fulltext IS NULL;

        CREATE INDEX IF NOT EXISTS bookmarks_unretrieved
            ON bookmarks (retrieved, url)
            WHERE retrieved IS NULL;

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

        self.add_full_text()

    def start(self) -> None:
        """Define the CherryPy messages to listen for.

        This plugin owns the bookmarks prefix.

        It depends on the urlfetch plugin for URL retrieval.
        """

        self.bus.subscribe("server:ready", self.setup)
        self.bus.subscribe("bookmarks:find:id", self.find_id)
        self.bus.subscribe("bookmarks:find:url", self.find_url)
        self.bus.subscribe("bookmarks:add", self.add)
        self.bus.subscribe("bookmarks:add:fulltext", self.add_full_text)
        self.bus.subscribe("bookmarks:domaincount", self.domain_count)
        self.bus.subscribe("bookmarks:search", self.search)
        self.bus.subscribe("bookmarks:prune", self.prune)
        self.bus.subscribe("bookmarks:recent", self.recent)
        self.bus.subscribe("bookmarks:tags:all", self.all_tags)
        self.bus.subscribe("bookmarks:remove", self.remove)
        self.bus.subscribe("bookmarks:repair", self.repair)

    def find_id(self, uid: int) -> Optional[sqlite3.Row]:
        """Locate a bookmark by ID."""

        sql = """SELECT rowid, url as 'url [url]', title,
            added as 'added [local_datetime]',
            updated as 'updated [local_datetime]',
            deleted as 'deleted [local_datetime]',
            tags, comments
            FROM bookmarks
            WHERE rowid=?"""
        return self._selectOne(sql, (uid,))

    def find_url(self, url: Url) -> Optional[sqlite3.Row]:
        """Locate a bookmark by URL."""

        sql = """SELECT rowid, url as 'url [url]', title,
            added as 'added [local_datetime]',
            updated as 'updated [local_datetime]',
            deleted as 'deleted [local_datetime]',
            tags, comments
            FROM bookmarks
            WHERE domain=? AND url=?"""
        return self._selectOne(sql, (url.domain, url.address))

    @decorators.log_runtime
    def add(self,
            url: Url,
            title: str = None,
            comments: str = None,
            tags: str = None,
            added: str = None) -> bool:
        """Store a bookmarked URL and its metadata."""

        bookmark = self.find_url(url)

        if bookmark:
            self._execute(
                """UPDATE bookmarks
                SET title=?, tags=?, comments=?,
                updated=CURRENT_TIMESTAMP,
                deleted=NULL WHERE rowid=?""",
                (
                    title,
                    tags,
                    comments,
                    bookmark["rowid"]
                )
            )

            return True

        if added and added.isnumeric():
            add_date = cherrypy.engine.publish(
                "clock:from_timestamp",
                int(added)
            ).pop()
        else:
            add_date = cherrypy.engine.publish(
                "clock:now",
            ).pop()

        add_date_formatted = cherrypy.engine.publish(
            "clock:format",
            add_date,
            "%Y-%m-%d %H:%M:%S"
        ).pop()

        self._execute(
            """INSERT INTO bookmarks
            (domain, url, added, title, tags, comments)
            VALUES (?, ?, ?, ?, ?, ?)""",
            (
                url.domain,
                url.address,
                add_date_formatted,
                title,
                tags,
                comments
            )
        )

        if tags:
            cherrypy.engine.publish(
                "cache:clear",
                "bookmarks:all_tags"
            )

        cherrypy.engine.publish(
            "scheduler:add",
            2,
            "bookmarks:add:fulltext"
        )

        cherrypy.engine.publish(
            "scheduler:add",
            5,
            "bookmarks:tags:all",
            for_precache=True
        )

        return True

    def add_full_text(self) -> None:
        """Store the plain text of a bookmarked URL.

        This is only used for searching.
        """

        url = self._selectFirst("""
        SELECT url as 'url [url]'
        FROM bookmarks
        WHERE retrieved IS NULL
        LIMIT 1""")

        if not url:
            return

        html = cherrypy.engine.publish(
            "urlfetch:get",
            url.address
        ).pop()

        text = cherrypy.engine.publish(
            "markup:plaintext",
            html,
            url
        ).pop()

        self._execute(
            """UPDATE bookmarks
            SET fulltext=?, retrieved=CURRENT_TIMESTAMP
            WHERE url=?""",
            (text, url.address)
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

    def domain_count(self, url: Url) -> int:
        """Count the number of bookmarks for a given domain."""

        sql = """SELECT count(*) FROM bookmarks WHERE domain=?"""

        if "reddit.com" not in url.domain:
            count = self._selectFirst(sql, (url.domain,))
        else:
            sql += " AND url LIKE ?"
            count = self._selectFirst(
                sql,
                (url.domain, f"%{url.display_domain}%")
            )

        return int(count)

    @decorators.log_runtime
    def remove(self, uid: int) -> int:
        """Discard a previously bookmarked URL."""

        bookmark = self.find_id(uid)

        deletions = 0

        if bookmark:
            deletions = self._delete(
                "UPDATE bookmarks SET deleted=CURRENT_TIMESTAMP WHERE rowid=?",
                (bookmark["rowid"],)
            )

            if bookmark["tags"]:
                cherrypy.engine.publish("cache:clear", "bookmarks:all_tags")

        return deletions

    @decorators.log_runtime
    def search(
            self,
            query: str,
            order: str = "rank",
            limit: int = 20,
            offset: int = 0
    ) -> Tuple[
        List[sqlite3.Row], int, List[str]
    ]:
        """Locate bookmarks via fulltext search.

        Ranking is based on the built-in hidden rank column provided
        by Sqlite FTS5, which the Sqlite documentation indicates is
        faster than using the bm25() function and specifying custom
        weights for each column.

        In testing, there wasn't a huge difference between the two.

        """

        from_sql = "bookmarks b"
        where_sql = "b.deleted IS NULL"
        placeholder_values: Tuple[str, ...] = ()
        order_sql = "b.added DESC"

        if "tag:" in query:
            query = query.replace("tag:", "tags:")

        if "comment:" in query:
            query = query.replace("comment:", "comments:")

        if "site:" in query:
            match = re.search(r"site:\s*(\S+)", query)
            if match:
                where_sql += " AND b.domain=?"

                domain = match.group(1)
                path = ""
                if domain.startswith("/r/"):
                    domain = "www.reddit.com"
                    path = f"%{match.group(1)}%"
                    where_sql += " AND b.url LIKE ?"

                placeholder_values += (domain,)

                if path:
                    placeholder_values += (path,)

                query = query.replace(match.group(0), "")

        if query:
            # The query is sanitized to prevent FTS5 syntax errors.
            query = re.sub(r"[^\w\" ]", "_", query)

            # Semicolons are allowed after column names.
            query = re.sub(
                r"\b(title|tags|comments)_\s*", r"\g<1>:",
                query
            )

            from_sql = "bookmarks_fts, bookmarks b"
            where_sql += """ AND bookmarks_fts.rowid=b.rowid
            AND bookmarks_fts MATCH ?"""

            if order == "rank":
                order_sql = "bookmarks_fts.rank"
            if order == "date-asc":
                order_sql = "b.added ASC"

            placeholder_values += (query,)

        sql = f"""SELECT b.rowid, b.url as 'url [url]', b.title,
        b.comments, b.tags as 'tags [comma_delimited]',
        added as 'added [local_datetime]',
        updated as 'updated [local_datetime]'
        FROM {from_sql}
        WHERE {where_sql}
        ORDER BY {order_sql}
        LIMIT ? OFFSET ?"""  # nosec

        placeholder_values += (
            str(limit),
            str(offset)
        )

        return (
            self._select(sql, placeholder_values),
            self._count(sql, placeholder_values),
            self._explain(sql, placeholder_values)
        )

    @decorators.log_runtime
    def recent(
            self,
            limit: int = 20,
            offset: int = 0,
            max_days: int = 180
    ) -> Tuple[
        List[sqlite3.Row], int, List[str]
    ]:
        """Get a newest-first list of recently bookmarked URLs."""

        sql = """SELECT rowid, url as 'url [url]', domain, title,
        added as 'added [timestamp]',
        updated as 'updated [timestamp]',
        retrieved 'retrieved [timestamp]',
        comments, tags as 'tags [comma_delimited]'
        FROM bookmarks
        WHERE substr(added, 0, 11) >= date('now', ?)
        AND deleted IS NULL
        ORDER BY added DESC
        LIMIT ? OFFSET ?"""

        max_days_clause = f"-{max_days} day"

        return (
            self._select(sql, (max_days_clause, limit, offset)),
            self._count(sql, (max_days_clause,)),
            self._explain(sql, (max_days_clause, limit, offset))
        )

    def all_tags(
            self,
            for_precache: bool = False
    ) -> Union[None, List[str]]:
        """Get the full list of all known tags."""

        cache_key = "bookmarks:all_tags"

        cached_tags: str = cherrypy.engine.publish(
            "cache:get",
            cache_key
        ).pop()

        if cached_tags:
            return list(cached_tags)

        sql = """SELECT distinct tags as 'tags [comma_delimited]'
        FROM bookmarks
        WHERE tags IS NOT NULL
        AND deleted IS NULL
        AND tags <> ''
        """

        generator = self._select_generator(sql)

        tags: Set[str] = set()
        for row in generator:
            tags.update(row["tags"])

        sorted_tags = sorted(tags)

        cherrypy.engine.publish(
            "cache:set",
            cache_key,
            sorted_tags
        )

        if not for_precache:
            return sorted_tags

        return None

    @decorators.log_runtime
    def prune(self) -> None:
        """Delete rows that have been marked for removal.

        This is normally invoked from the maintenance plugin.

        """

        deletion_count = self._delete(
            "DELETE FROM bookmarks WHERE deleted IS NOT NULL"
        )

        unit = "row" if deletion_count == 1 else "rows"

        cherrypy.engine.publish(
            "applog:add",
            "bookmarks",
            f"{deletion_count} {unit} deleted"
        )

        if deletion_count > 0:
            cherrypy.engine.publish(
                "cache:clear",
                "bookmarks:all_tags"
            )

    @decorators.log_runtime
    def repair(self) -> None:
        """Correct wrong or missing values."""

        rows_without_domain = self._select_generator(
            """SELECT rowid, url as 'url [url]'
            FROM bookmarks
            WHERE domain IS NULL"""
        )

        for row in rows_without_domain:
            self._execute(
                "UPDATE bookmarks SET domain=? WHERE rowid=?",
                (row["url"].domain, row["id"])
            )
