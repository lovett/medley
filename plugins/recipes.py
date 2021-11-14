"""Document storage for recipes."""

from datetime import datetime
import sqlite3
import typing
import cherrypy
from plugins import mixins
from plugins import decorators
from resources.url import Url


class Plugin(cherrypy.process.plugins.SimplePlugin, mixins.Sqlite):
    """Document-oriend storage of recipes via SQLite."""

    def __init__(self, bus: cherrypy.process.wspbus.Bus) -> None:
        cherrypy.process.plugins.SimplePlugin.__init__(self, bus)

        self.db_path = self._path("recipes.sqlite")

    def setup(self) -> None:
        """Create the database."""

        self._create("""
        PRAGMA journal_mode=WAL;
        PRAGMA foreign_keys=ON;

        CREATE TABLE IF NOT EXISTS recipes (
            id INTEGER PRIMARY KEY,
            title NOT NULL,
            body TEXT NOT NULL,
            url TEXT DEFAULT NULL,
            domain TEXT default NULL,
            created DEFAULT CURRENT_TIMESTAMP,
            updated DEFAULT NULL,
            deleted DEFAULT NULL,
            last_made DEFAULT NULL,
            starred DEFAULT NULL
        );

        CREATE INDEX IF NOT EXISTS index_recipe_last_made
            ON recipes (last_made) WHERE last_made IS NOT NULL;

        CREATE INDEX IF NOT EXISTS index_recipe_starred
            ON recipes (starred) WHERE starred IS NOT NULL;

        CREATE TABLE IF NOT EXISTS recipe_tag (
            recipe_id INT NOT NULL,
            tag_id INT NOT NULL,
            PRIMARY KEY (recipe_id, tag_id),
            FOREIGN KEY (recipe_id) REFERENCES recipes(id)
                ON DELETE CASCADE,
            FOREIGN KEY (tag_id) REFERENCES tags(id)
                ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS attachments (
            id INTEGER PRIMARY KEY,
            recipe_id INT NOT NULL,
            filename TEXT NOT NULL,
            mime_type TEXT NOT NULL,
            content BLOB NOT NULL,
            created DEFAULT CURRENT_TIMESTAMP,
            deleted DEFAULT NULL,
            FOREIGN KEY (recipe_id) REFERENCES recipes(id)
                ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS index_attachment_recipe_id
            ON attachments (recipe_id);

        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL
        );

        CREATE UNIQUE INDEX IF NOT EXISTS tag_name
            ON tags(name);

        CREATE VIRTUAL TABLE IF NOT EXISTS recipes_fts USING fts5 (
            title,
            body,
            domain,
            content=recipes,
            tokenize=porter
        );

        CREATE TRIGGER IF NOT EXISTS recipes_after_insert
        AFTER INSERT ON recipes
        BEGIN
        INSERT INTO recipes_fts (rowid, title, body, domain)
        VALUES (new.rowid, new.title, new.body, new.domain);
        END;

        CREATE TRIGGER IF NOT EXISTS recipes_after_update
        AFTER UPDATE OF title, body ON recipes
        BEGIN
        UPDATE recipes SET updated=CURRENT_TIMESTAMP WHERE id=new.rowid;
        INSERT INTO recipes_fts (recipes_fts, rowid, title, body, domain)
            VALUES ('delete', old.rowid, old.title, old.body, old.domain);
        INSERT INTO recipes_fts (rowid, title, body, domain)
            VALUES (new.rowid, new.title, new.body, new.domain);
        END;

        CREATE TRIGGER IF NOT EXISTS recipes_after_delete
        AFTER DELETE ON recipes
        BEGIN
        INSERT INTO recipes_fts(recipes_fts, rowid, title, body, domain)
            VALUES ('delete', old.rowid, old.title, old.body, old.domain);
        END;

        CREATE TRIGGER IF NOT EXISTS recipe_tag_after_delete
        AFTER DELETE ON recipe_tag
        BEGIN
        DELETE FROM tags
            WHERE id NOT IN (SELECT DISTINCT tag_id FROM recipe_tag);
        END;

        CREATE VIEW IF NOT EXISTS extended_recipes_view AS
            SELECT recipes.id, title, body, url, domain,
                created, updated, last_made, starred,
                GROUP_CONCAT(tags.name) as tags
            FROM recipes
            LEFT JOIN recipe_tag
                ON recipes.id=recipe_tag.recipe_id
            LEFT JOIN tags
                ON recipe_tag.tag_id=tags.id
            WHERE recipes.deleted IS NULL
            GROUP BY recipes.id;
        """)

    def start(self) -> None:
        """Define the CherryPy messages to listen for.

        This plugin owns the recipes prefix.
        """

        self.bus.subscribe("server:ready", self.setup)
        self.bus.subscribe("recipes:attachment:list", self.list_attachments)
        self.bus.subscribe("recipes:attachment:view", self.view_attachment)
        self.bus.subscribe("recipes:attachment:remove", self.remove_attachment)
        self.bus.subscribe("recipes:tags:all", self.all_tags)
        self.bus.subscribe("recipes:find", self.find)
        self.bus.subscribe("recipes:find:tag", self.find_by_tag)
        self.bus.subscribe("recipes:find:recent", self.find_recent)
        self.bus.subscribe("recipes:find:starred", self.find_starred)
        self.bus.subscribe("recipes:prune", self.prune)
        self.bus.subscribe("recipes:remove", self.remove)
        self.bus.subscribe("recipes:search:date", self.search_by_date)
        self.bus.subscribe("recipes:search:keyword", self.search_by_keyword)
        self.bus.subscribe("recipes:toggle:star", self.toggle_star)
        self.bus.subscribe("recipes:upsert", self.upsert)

    def list_attachments(
            self,
            recipe_id: int
    ) -> typing.List[sqlite3.Row]:
        """List the files currently associated with a recipe."""

        return self._select(
            """SELECT id, filename, mime_type
            FROM attachments
            WHERE recipe_id=?
            AND deleted IS NULL
            ORDER BY filename""",
            (recipe_id,)
        )

    def view_attachment(self, recipe_id: int, filename: str) -> bytes:
        """Get the bytes of an attachment."""

        return typing.cast(
            bytes,
            self._selectOne(
                """SELECT filename, mime_type, content
                FROM attachments
                WHERE recipe_id=?
                AND filename=?""",
                (recipe_id, filename)
            )
        )

    def all_tags(self) -> typing.Iterator[sqlite3.Row]:
        """List all known tags.

        This is a three-join table to accommodate soft deletion. A
        recipe-to-tag relation remains until recipes that have been
        marked as deleted are actually dropped from the database
        during pruning.
        """

        return self._select_generator(
            """SELECT name, count(*) as count
            FROM tags JOIN recipe_tag ON tags.id=recipe_tag.tag_id
            JOIN recipes ON recipe_tag.recipe_id=recipes.id
            WHERE recipes.deleted IS NULL
            GROUP BY recipe_tag.tag_id
            ORDER BY name"""
        )

    def find(self, recipe_id: int) -> typing.Optional[sqlite3.Row]:
        """Locate a recipe by its ID."""

        return self._selectOne(
            """SELECT id, title, body, url, domain,
            created as 'created [local_datetime]',
            updated as 'updated [local_datetime]',
            starred as 'starred [local_datetime]',
            last_made as 'last_made [date]',
            tags as 'tags [comma_delimited]'
            FROM extended_recipes_view
            WHERE id=?""",
            (recipe_id,)
        )

    def find_recent(self, limit: int = 12) -> typing.Iterator[sqlite3.Row]:
        """Locate recently-added recipes."""

        return self._select_generator(
            """SELECT id, title, url, domain,
            created as 'created [local_datetime]',
            updated as 'updated [local_datetime]',
            last_made as 'last_made [date]',
            tags as 'tags [comma_delimited]'
            FROM extended_recipes_view
            ORDER BY created DESC LIMIT ?
            """,
            (limit,)
        )

    def find_starred(self, limit: int = 20) -> typing.Iterator[sqlite3.Row]:
        """Locate starred recipes."""

        return self._select_generator(
            """SELECT id, title, url, domain,
            created as 'created [local_datetime]',
            updated as 'updated [local_datetime]',
            starred as 'starred [local_datetime]',
            last_made as 'last_made [date]',
            tags as 'tags [comma_delimited]'
            FROM extended_recipes_view
            WHERE starred IS NOT NULL
            ORDER BY starred DESC LIMIT ?
            """,
            (limit,)
        )

    def find_by_tag(self, tag: str) -> typing.Iterator[sqlite3.Row]:
        """List all recipes associated with a tag."""

        return self._select_generator(
            """SELECT id, title, url, domain,
            created as 'created [local_datetime]',
            updated as 'updated [local_datetime]',
            last_made as 'last_made [date]',
            tags as 'tags [comma_delimited]'
            FROM extended_recipes_view
            WHERE id IN (
                SELECT recipe_id
                FROM recipe_tag, tags
                WHERE recipe_tag.tag_id=tags.id
                AND tags.name=?
            )""",
            (tag,)
        )

    @decorators.log_runtime
    def prune(self) -> None:
        """Delete recipe and attachment rows that have been marked for removal.

        This is normally invoked from the maintenance plugin.

        """

        for table in ("recipes", "attachments"):
            deletion_count = self._delete(
                f"DELETE FROM {table} WHERE deleted IS NOT NULL"
            )

            unit = "row" if deletion_count == 1 else "rows"

            cherrypy.engine.publish(
                "applog:add",
                "recipes",
                f"{deletion_count} {table} {unit} deleted"
            )

    @decorators.log_runtime
    def remove(self, recipe_id: int) -> bool:
        """Mark a recipe for future deletion."""

        return self._execute(
            "UPDATE recipes SET deleted=CURRENT_TIMESTAMP WHERE id=?",
            (recipe_id,)
        )

    def remove_attachment(self, recipe_id: int, attachment_id: int) -> bool:
        """Mark an attachment for future deletion."""
        return self._execute(
            """UPDATE attachments
            SET deleted=CURRENT_TIMESTAMP
            WHERE recipe_id=? AND id=?""",
            (recipe_id, attachment_id)
        )

    def search_by_date(
            self,
            field: str,
            query_date: datetime
    ) -> typing.Iterator[sqlite3.Row]:
        """Locate recipes that match a date search."""

        month_start = cherrypy.engine.publish(
            "clock:shift",
            query_date,
            "month_start"
        ).pop()

        month_end = cherrypy.engine.publish(
            "clock:shift",
            query_date,
            "month_end"
        ).pop()

        return self._select_generator(
            f"""SELECT r.id, r.title, r.body, r.url, r.domain,
            r.created as 'created [local_datetime]',
            r.updated as 'updated [local_datetime]',
            r.last_made as 'last_made [date]',
            r.tags as 'tags [comma_delimited]'
            FROM extended_recipes_view AS r
            WHERE (r.{field} BETWEEN ? and ?)
            ORDER BY r.{field} DESC""",
            (month_start, month_end)
        )

    def search_by_keyword(self, query: str) -> typing.Iterator[sqlite3.Row]:
        """Locate recipes that match a keyword search."""

        return self._select_generator(
            """SELECT r.id, r.title, r.body, r.url, r.domain,
            r.created as 'created [local_datetime]',
            r.updated as 'updated [local_datetime]',
            r.last_made as 'last_made [date]',
            r.tags as 'tags [comma_delimited]'
            FROM extended_recipes_view AS r, recipes_fts
            WHERE r.id=recipes_fts.rowid
            AND recipes_fts MATCH ?
            ORDER BY recipes_fts.rank DESC""",
            (query,)
        )

    def toggle_star(self, recipe_id: int) -> None:
        """If a recipe is not starred, star it. Otherwise, instar it."""

        self._execute(
            """UPDATE recipes SET starred=CASE
            WHEN starred IS NULL THEN CURRENT_TIMESTAMP
            ELSE NULL
            END where id=?""",
            (recipe_id,)
        )

    def upsert(
            self,
            recipe_id: int,
            **kwargs: typing.Any
    ) -> typing.Union[bool, int]:
        """Insert or update a recipe."""

        title = kwargs.get("title")
        body = kwargs.get("body")

        url = Url(kwargs.get("url") or "")
        last_made = kwargs.get("last_made")
        created = kwargs.get("created")
        tags = kwargs.get("tags", [])
        attachments = kwargs.get("attachments", [])

        upsert_id = None
        if recipe_id > 0:
            upsert_id = recipe_id

        queries: typing.List[typing.Tuple[str, typing.Tuple]] = []

        queries.append((
            """CREATE TEMP TABLE IF NOT EXISTS tmp
            (key TEXT, value TEXT)""",
            ()
        ))

        queries.append((
            """INSERT INTO recipes (id, title, body, domain, url, created, last_made)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (id) DO UPDATE SET
            title=excluded.title,
            body=excluded.body,
            domain=excluded.domain,
            url=excluded.url,
            created=excluded.created,
            last_made=excluded.last_made""",
            (upsert_id, title, body,
             url.domain, url.address,
             created, last_made)
        ))

        if upsert_id:
            queries.append((
                """INSERT INTO tmp (key, value)
                VALUES ("recipe_id", ?)""",
                (upsert_id,)
            ))
        else:
            queries.append((
                """INSERT INTO tmp (key, value)
                VALUES ("recipe_id", last_insert_rowid())""",
                ()
            ))

        if upsert_id:
            queries.append((
                """DELETE FROM recipe_tag WHERE recipe_id=?""",
                (upsert_id,)
            ))

        for tag in tags:
            queries.append((
                """INSERT OR IGNORE INTO tags (name) VALUES (?)""",
                (tag,)
            ))

            queries.append((
                """INSERT INTO recipe_tag (recipe_id, tag_id)
                VALUES (
                    (SELECT value FROM tmp WHERE key="recipe_id"),
                    (SELECT id FROM tags WHERE name=?)
                )""",
                (tag,)
            ))

        for attachment in attachments:
            queries.append((
                """INSERT INTO attachments (recipe_id, filename, mime_type, content)
                VALUES (
                    (SELECT value FROM tmp WHERE key="recipe_id"),
                    ?, ?, ?
                )""",
                (attachment[0], attachment[1], attachment[2])
            ))

        after_commit = ("SELECT value FROM tmp WHERE key='recipe_id'", ())

        result = self._multi(queries, after_commit)

        if isinstance(result, bool):
            return result

        return typing.cast(int, next(result)["value"])
