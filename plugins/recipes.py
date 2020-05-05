"""Document storage for recipes."""

import sqlite3
import typing
import cherrypy
import pendulum
from . import mixins
from . import decorators


class Plugin(cherrypy.process.plugins.SimplePlugin, mixins.Sqlite):
    """Document-oriend storage of recipes via SQLite."""

    def __init__(self, bus: cherrypy.process.wspbus.Bus) -> None:
        cherrypy.process.plugins.SimplePlugin.__init__(self, bus)

        self.db_path = self._path("recipes.sqlite")

        self._create("""
        PRAGMA journal_mode=WAL;
        PRAGMA foreign_keys=ON;

        CREATE TABLE IF NOT EXISTS recipes (
            id INTEGER PRIMARY KEY,
            title NOT NULL,
            body TEXT NOT NULL,
            url TEXT DEFAULT NULL,
            created DEFAULT CURRENT_TIMESTAMP,
            updated DEFAULT NULL,
            deleted DEFAULT NULL,
            last_made DEFAULT NULL
        );

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
            content=recipes,
            tokenize=porter
        );

        CREATE TRIGGER IF NOT EXISTS recipes_after_insert
        AFTER INSERT ON recipes
        BEGIN
        INSERT INTO recipes_fts (rowid, title, body)
        VALUES (new.rowid, new.title, new.body);
        END;

        CREATE TRIGGER IF NOT EXISTS recipes_after_update
        AFTER UPDATE OF title, body ON recipes
        BEGIN
        UPDATE recipes SET updated=CURRENT_TIMESTAMP WHERE id=new.rowid;
        INSERT INTO recipes_fts (recipes_fts, rowid, title, body)
            VALUES ('delete', old.rowid, old.title, old.body);
        INSERT INTO recipes_fts (rowid, title, body)
            VALUES (new.rowid, new.title, new.body);
        END;

        CREATE TRIGGER IF NOT EXISTS recipes_after_delete
        AFTER DELETE ON recipes
        BEGIN
        INSERT INTO recipes_fts(recipes_fts, rowid, title, body)
            VALUES ('delete', old.rowid, old.title, old.body);
        END;

        CREATE TRIGGER IF NOT EXISTS recipe_tag_after_delete
        AFTER DELETE ON recipe_tag
        BEGIN
        DELETE FROM tags
            WHERE id NOT IN (SELECT DISTINCT tag_id FROM recipe_tag);
        END;

        CREATE VIEW IF NOT EXISTS extended_recipes_view AS
            SELECT recipes.id, title, body, url,
                created, updated, last_made,
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

        self.bus.subscribe("recipes:add", self.add)
        self.bus.subscribe("recipes:attachment:add", self.attach)
        self.bus.subscribe("recipes:attachment:list", self.list_attachments)
        self.bus.subscribe("recipes:attachment:view", self.view_attachment)
        self.bus.subscribe("recipes:attachment:remove", self.remove_attachment)
        self.bus.subscribe("recipes:tags:all", self.all_tags)
        self.bus.subscribe("recipes:find", self.find)
        self.bus.subscribe("recipes:find:tag", self.find_by_tag)
        self.bus.subscribe("recipes:find:newest_id", self.find_newest_id)
        self.bus.subscribe("recipes:prune", self.prune)
        self.bus.subscribe("recipes:remove", self.remove)
        self.bus.subscribe("recipes:search:recipe", self.search_recipes)
        self.bus.subscribe("recipes:update", self.update)

    def add(self, **kwargs: typing.Any) -> bool:
        """Add a new recipe to the database."""

        title = kwargs.get("title")
        body = kwargs.get("body")
        url = kwargs.get("url") or None

        try:
            last_made = pendulum.from_format(
                kwargs.get("last_made", ""),
                "YYYY-MM-DD",
            ).format('YYYY-MM-DD')
        except (TypeError, ValueError):
            last_made = None

        tags = [
            item.strip()
            for item in kwargs.get("tags", "").split(",")
            if item
        ]

        if not tags:
            tags = ["untagged"]

        queries = [
            (
                """CREATE TEMP TABLE IF NOT EXISTS tmp
                (key TEXT, value TEXT)""",
                ()
            ),

            (
                """INSERT INTO recipes (title, body, url, last_made)
                VALUES (?, ?, ?, ?)""",
                (title, body, url, last_made)
            ),

            (
                """INSERT INTO tmp (key, value)
                VALUES ("recipe_id", last_insert_rowid())""",
                ()
            )
        ]

        for tag in tags:
            queries.append((
                """INSERT OR IGNORE INTO tags (name) VALUES (LOWER(?))""",
                (tag,)
            ))

            queries.append((
                """INSERT INTO recipe_tag (recipe_id, tag_id)
                VALUES (
                    (SELECT value FROM tmp WHERE key="recipe_id"),
                    (SELECT id FROM tags WHERE name=?)
                )""",
                (tag, )
            ))

        return self._multi(queries)

    # pylint: disable=protected-access
    def attach(
            self,
            recipe_id: int,
            filename: str,
            mime_type: str,
            content: bytes
    ) -> None:
        """Store one or more uploaded files associated with a recipe."""

        self._execute(
            """INSERT INTO attachments (recipe_id, filename, mime_type, content)
            VALUES (?, ?, ?, ?)""",
            (recipe_id, filename.lower(), mime_type, content)
        )

    def remove_attachment(
            self,
            recipe_id: int,
            attachment_id: int
    ) -> bool:
        """Discard an attachment."""
        return self._execute(
            "DELETE FROM attachments WHERE recipe_id=? AND id=?",
            (recipe_id, attachment_id)
        )

    def list_attachments(
            self,
            recipe_id: int
    ) -> typing.List[sqlite3.Row]:
        """List the files currently associated with a recipe."""

        return self._select(
            """SELECT id, filename, mime_type
            FROM attachments
            WHERE recipe_id=?
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
            """SELECT id, title, body, url,
            created as 'created [datetime]',
            updated as 'updated [datetime]',
            last_made as 'last_made [date]',
            tags as 'tags [comma_delimited]'
            FROM extended_recipes_view
            WHERE id=?""",
            (recipe_id,)
        )

    def find_by_tag(self, tag: str) -> typing.Iterator[sqlite3.Row]:
        """List all recipes associated with a tag."""
        return self._select_generator(
            """SELECT id, title, url,
            created as 'created [datetime]',
            updated as 'updated [datetime]',
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

    def find_newest_id(self) -> int:
        """Locate the most recently inserted recipe."""
        return typing.cast(
            int,
            self._selectFirst("SELECT MAX(id) FROM recipes")
        )

    @decorators.log_runtime
    def prune(self) -> None:
        """Delete rows that have been marked for removal.

        This is normally invoked from the maintenance plugin.

        """
        deletion_count = self._delete(
            "DELETE FROM recipes WHERE deleted IS NOT NULL"
        )

        unit = "row" if deletion_count == 1 else "rows"

        cherrypy.engine.publish(
            "applog:add",
            "recipes",
            f"{deletion_count} {unit} deleted"
        )

    @decorators.log_runtime
    def remove(self, recipe_id: int) -> bool:
        """Mark a recipe for future deletion."""

        return self._execute(
            "UPDATE recipes SET deleted=CURRENT_TIMESTAMP WHERE id=?",
            (recipe_id,)
        )

    def search_recipes(self, query: str) -> typing.Iterator[sqlite3.Row]:
        """Locate recipes that match a keyword search."""
        return self._select_generator(
            """SELECT r.id, r.title, r.body, r.url,
            r.created as 'created [datetime]',
            r.updated as 'updated [datetime]',
            r.last_made as 'last_made [datetime]',
            r.tags as 'tags [comma_delimited]'
            FROM extended_recipes_view AS r, recipes_fts
            WHERE r.id=recipes_fts.rowid
            AND recipes_fts MATCH ?
            ORDER BY recipes_fts.rank DESC""",
            (query,)
        )

    def update(self, recipe_id: int, **kwargs: typing.Any) -> bool:
        """Replace an existing recipe with new values."""

        title = kwargs.get("title")
        body = kwargs.get("body")
        url = kwargs.get("url") or None

        try:
            last_made = pendulum.from_format(
                kwargs.get("last_made", ""),
                "YYYY-MM-DD",
            ).format('YYYY-MM-DD')
        except (TypeError, ValueError):
            last_made = None

        tags = [
            item.strip()
            for item in kwargs.get("tags", "").split(",")
            if item
        ]

        if not tags:
            tags = ["untagged"]

        queries = [
            (
                """UPDATE recipes
                SET title=?, body=?, url=?, last_made=?
                WHERE id=?""",
                (title, body, url, last_made, recipe_id)
            ),
            (
                """DELETE FROM recipe_tag WHERE recipe_id=?""",
                (recipe_id,)
            )
        ]

        for tag in tags:
            queries.append((
                """INSERT OR IGNORE INTO tags (name) VALUES (?)""",
                (tag,)
            ))

            queries.append((
                """INSERT INTO recipe_tag (recipe_id, tag_id)
                VALUES (
                    ?,
                    (SELECT id FROM tags WHERE name=?)
                )""",
                (recipe_id, tag, )
            ))

        return self._multi(queries)
