"""Store arbitrary values in an SQLite database."""

from datetime import datetime
import json
from sqlite3 import Row
from typing import Any
from typing import List
from typing import Iterator
from typing import Tuple
from typing import Dict
from typing import cast
import cherrypy
from resources.url import Url
from . import mixins


class Plugin(cherrypy.process.plugins.SimplePlugin, mixins.Sqlite):
    """A CherryPy plugin for caching arbitrary values to disk."""

    def __init__(self, bus: cherrypy.process.wspbus.Bus) -> None:
        cherrypy.process.plugins.SimplePlugin.__init__(self, bus)

        self.db_path = self._path("cache.sqlite")

    def setup(self) -> None:
        """Create the database."""

        self._create("""
        PRAGMA journal_mode=WAL;

        CREATE TABLE IF NOT EXISTS cache (
            prefix TEXT,
            key TEXT,
            value BLOB,
            expires TEXT,
            created TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE UNIQUE INDEX IF NOT EXISTS index_prefix_and_key
            ON cache(prefix, key);

        CREATE VIEW IF NOT EXISTS unexpired AS
            SELECT prefix, key, value, expires, created
            FROM cache
            WHERE expires > datetime('now');
        """)

        cherrypy.engine.publish("cache:ready")

    def start(self) -> None:
        """Define the CherryPy messages to listen for.

        This plugin owns the cdr prefix.
        """

        self.bus.subscribe("server:ready", self.setup)
        self.bus.subscribe("cache:info", self.info)
        self.bus.subscribe("cache:get", self.get)
        self.bus.subscribe("cache:reddit:index", self.reddit_index)
        self.bus.subscribe("cache:reddit:story", self.reddit_story)
        self.bus.subscribe("cache:headlines", self.headlines)
        self.bus.subscribe(
            "cache:reddit:pagination",
            self.reddit_pagination
        )
        self.bus.subscribe("cache:check", self.check)
        self.bus.subscribe("cache:mget", self.mget)
        self.bus.subscribe("cache:match", self.match)
        self.bus.subscribe("cache:set", self.set)
        self.bus.subscribe("cache:clear", self.clear)
        self.bus.subscribe("cache:prune", self.prune)

    @staticmethod
    def keysplit(key: str) -> Tuple[str, str]:
        """Break a key into two parts."""

        if ":" in key:
            return cast(
                Tuple[str, str],
                tuple(key.split(":", 1))
            )

        return ("_", key)

    def info(self, key: str) -> Dict[str, Any]:
        """Date and age details for a cached value."""

        prefix, rest = self.keysplit(key)

        row = self._selectOne(
            """SELECT
            created as 'cached_on [local_datetime]',
            expires as 'cached_until [local_datetime]',
            unixepoch() - unixepoch(created) as cache_age_sec,
            unixepoch(expires) - unixepoch() as cache_remaining_sec
            FROM unexpired
            WHERE prefix=? AND key=?""",
            (prefix, rest)
        )

        if row:
            return dict(row)

        return {}

    def match(self, prefix: str) -> Iterator[Any]:
        """Retrieve multiple values based on a common prefix."""

        rows = self._select_generator(
            """SELECT value
            FROM unexpired
            WHERE prefix=?""",
            (prefix,)
        )

        for row in rows:
            if not isinstance(row["value"], str):
                yield row["value"]
                continue
            try:
                yield json.loads(row["value"])
            except json.decoder.JSONDecodeError:
                yield row["value"]

    def mget(self, keys: Tuple[str, ...]) -> Iterator[Tuple[Any, datetime]]:
        """Retrieve multiple values."""

        filters = []
        placeholders: List[str] = []
        for key in keys:
            prefix, rest = self.keysplit(key)
            placeholders.append(prefix)
            placeholders.append(rest)
            filters.append("(prefix=? AND key=?)")

        sql = f"""SELECT key, value, created as 'created [local_datetime]'
        FROM unexpired
        WHERE {" or ".join(filters)}"""

        rows = self._select_generator(sql, placeholders)

        for row in rows:
            key, value, created = row
            if not isinstance(value, str):
                yield (value, created)
                continue
            try:
                yield (json.loads(value), created)
            except json.decoder.JSONDecodeError:
                yield (value, created)

    def check(self, key: str) -> bool:
        """Determine if a key exists in the check."""

        prefix, rest = self.keysplit(key)

        return bool(self._selectFirst(
            """SELECT count(*)
            FROM unexpired
            WHERE prefix=? AND key=?""",
            (prefix, rest)
        ))

    def reddit_pagination(self, url: Url) -> Dict[str, Any]:
        """Extract values needed to build Reddit pagination links."""

        prefix, rest = self.keysplit(url.address)

        row = self._selectOne(
            """SELECT
            json_extract(u.value, '$.data.before') as before,
            json_extract(u.value, '$.data.after') as after,
            json_extract(u.value, '$.data.dist') as count
            FROM unexpired u
            WHERE u.prefix=? AND u.key=?""",
            (prefix, rest)
        )

        if row:
            return dict(row)
        return {}

    def headlines(self, endpoint: Url) -> Iterator[Row]:
        """Render a list of headlines."""

        prefix, rest = self.keysplit(endpoint.address)

        return self._select_generator(
            """SELECT
            j.value ->> '$.url' as 'url [url]',
            j.value ->> '$.title' as title
            FROM unexpired u, json_each(u.value, '$.articles') j
            WHERE u.prefix=? AND u.key=?
            AND j.value ->> '$.title' <> '[Removed]'
            """,
            (prefix, rest)
        )

    def reddit_index(self, endpoint: Url) -> Iterator[Row]:
        """Render a list of stories."""

        prefix, rest = self.keysplit(endpoint.address)

        return self._select_generator(
            """SELECT
            j.value ->> '$.data.title' as title,
            j.value ->> '$.data.url' as 'url [url]',
            j.value ->> '$.data.domain' as domain,
            FORMAT('https://reddit.com%s', j.value ->> '$.data.permalink')
              AS 'permalink [url]',
            j.value ->> '$.data.num_comments' as 'num_comments',
            LENGTH(IFNULL(j.value ->> '$.data.selftext', '')) > 0 as selftext,
            FORMAT('https://reddit.com/r/%s', j.value ->> '$.data.subreddit')
              AS 'subreddit [url]',
            j.value ->> '$.data.created_utc' as created_utc
            FROM unexpired u, json_each(u.value, '$.data.children') j
            WHERE u.prefix=? AND u.key=?
            AND json_extract(u.value, j.fullkey || '.kind') == 't3'
            ORDER BY j.value ->> '$.data.created_utc' DESC
            """,
            (prefix, rest)
        )

    def reddit_story(
            self,
            endpoint: Url
    ) -> Tuple[Dict[str, Any], Iterator[Row]]:
        """Render a story discussion."""

        prefix, rest = self.keysplit(endpoint.address)

        story_rows = self._select_generator(
            """SELECT
            j.key, j.value
            FROM unexpired u,
                 json_each(u.value, '$[0].data.children[0].data') j
            WHERE u.prefix=? AND u.key=?
            AND j.key IN (
                'selftext',
                'created_utc',
                'url',
                'subreddit',
                'title',
                'num_comments',
                'author',
                'domain',
                'num_crossposts'
            )
            UNION
            SELECT
              'author_url',
              FORMAT('https://reddit.com/u/%s',
                u.value ->> '$[0].data.children[0].data.author')
              FROM unexpired u
              WHERE u.prefix=? AND u.key=?
            UNION
            SELECT
              'subreddit_url',
              FORMAT('https://reddit.com/r/%s',
                u.value ->> '$[0].data.children[0].data.subreddit')
              FROM unexpired u
              WHERE u.prefix=? AND u.key=?
            """,
            (prefix, rest) * 3
        )

        story = {row["key"]: row["value"] for row in story_rows}

        comments = self._select_generator(
            """SELECT
            j.value ->> '$.id' AS id,
            j.value ->> '$.author' AS author,
            FORMAT('https://reddit.com/u/%s', j.value ->> '$.author')
              AS 'author_url [url]',
            j.value ->> '$.created_utc' AS created_utc,
            j.value ->> '$.parent_id' as parent_id,
            j.value ->> '$.body_html' as body_html
            FROM unexpired u, json_tree(u.value, '$[1].data.children') j
            WHERE u.prefix=? AND u.key=?
            AND j.key='data'
            AND j.value ->> '$.id' <> ''
            AND j.value ->> '$.author' != 'AutoModerator'
            """,
            (prefix, rest)
        )

        return (story, comments)

    def get(self, key: str, include_cache_date: bool = False) -> Any:
        """Retrieve a value from the store."""

        prefix, rest = self.keysplit(key)

        row = self._selectOne(
            """SELECT value, created as 'created [local_datetime]'
            FROM unexpired
            WHERE prefix=? AND key=?""",
            (prefix, rest)
        )

        value = None
        created = None
        if row:
            value = row["value"]
            created = row["created"]

        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.decoder.JSONDecodeError:
                pass

        if include_cache_date:
            return (value, created)

        return value

    def set(
            self,
            key: str,
            value: Any,
            lifespan_seconds: int = 604800
    ) -> bool:
        """Add a value to the store.

        If the value is anything other than bytes or a string, JSON
        encoding will be attempted. If the value cannot be JSON
        encoded, no caching will occur.

        """

        value_for_storage = value

        if isinstance(value, (dict, list, set)):
            try:
                value_for_storage = json.dumps(value)
            except TypeError:
                cherrypy.engine.publish(
                    "applog:add",
                    "cache:set",
                    f"A value for {key} could not be cached."
                )

                return False

        prefix, rest = self.keysplit(key)

        self._execute(
            """INSERT OR REPLACE INTO cache
            (prefix, key, value, expires)
            VALUES (?, ?, ?, datetime('now', ?))""",
            (
                prefix,
                rest,
                value_for_storage,
                f"{lifespan_seconds} seconds"
            )
        )

        return True

    def clear(self, key: str) -> int:
        """Remove a value from the store by its key."""

        prefix, rest = self.keysplit(key)

        deletion_count = self._delete(
            """DELETE FROM cache
            WHERE prefix=? AND key=?""",
            (prefix, rest)
        )

        unit = "row" if deletion_count == 1 else "rows"

        cherrypy.engine.publish(
            "applog:add",
            "cache:clear",
            f"{deletion_count} {unit} deleted"
        )

        return deletion_count

    def prune(self) -> None:
        """Delete expired cache entries."""

        deletion_count = self._delete(
            """DELETE FROM cache
            WHERE expires < datetime()"""
        )

        unit = "row" if deletion_count == 1 else "rows"

        cherrypy.engine.publish(
            "applog:add",
            "cache:prune",
            f"{deletion_count} {unit} deleted"
        )
