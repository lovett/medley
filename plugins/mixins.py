"""Methods for issuing SQL queries against an SQLite database."""

import os.path
import sqlite3
import re
import cherrypy


# pylint: disable=invalid-name,no-member
class Sqlite:
    """Query an SQLite database using Python's DB-API."""

    db_path = None

    @staticmethod
    def _path(name):
        """Get the filesystem path of a database file relative to the
        application database directory.

        """

        return os.path.join(
            cherrypy.config.get("database_dir"),
            name
        )

    def _open(self):
        """Open a connection to the current database."""

        return sqlite3.connect(
            self.db_path,
            detect_types=sqlite3.PARSE_COLNAMES
        )

    def _create(self, sql):
        """Establish a schema by executing a series of SQL statements.

        The statements should be re-runnable so that new objects will
        be created automatically. This can be accomplished with "IF
        NOT EXISTS" statements when creating tables and triggers.

        This approach is geared toward new objects. It won't account
        for modifications to existing objects such as ALTER TABLE.

        """

        con = self._open()
        con.cursor().executescript(sql)
        con.commit()
        con.close()

    def _execute(self, query, params=()):

        """Execute a single query with no parameters."""

        con = self._open()
        con.execute(query, params)
        con.commit()
        con.close()

    def _multi(self, queries):
        """Issue several queries."""

        con = self._open()
        with con:
            for query, params in queries:
                con.execute(query, params)
            con.commit()

    def _insert(self, query, values):
        """Issue an insert query to create one or more records."""

        con = self._open()
        with con:
            con.executemany(query, values)
        con.close()

        # cannot return lastrowid because it is not populated
        # during executemany
        return True

    def _update(self, query, values):
        """Issue an update query."""
        con = self._open()
        with con:
            con.executemany(query, values)
        con.close()
        return True

    def _delete(self, query, values=()):
        """Issue a delete query."""
        con = self._open()
        with con:
            row_count = con.execute(query, values).rowcount
        con.close()
        return row_count

    def _count(self, query, values=()):
        """Convert a select query to a count query and execute it."""

        count_query = re.sub(
            r"SELECT.*?(FROM.*)ORDER BY.*",
            r"SELECT count(*) \g<1>",
            query,
            flags=re.MULTILINE | re.DOTALL | re.IGNORECASE
        )

        placeholder_count = count_query.count('?')
        placeholder_values = values[0:placeholder_count]

        return self._selectFirst(
            count_query,
            placeholder_values
        )

    def _select(self, query, values=()):
        """Issue a select query."""
        con = self._open()
        con.row_factory = sqlite3.Row

        with con:
            cur = con.cursor()
            cur.execute(query, values)
            return cur.fetchall() or []

    def _select_generator(self, query, values=(), arraysize=1):
        """Issue a select query and return results as a generator.

        Nearly the same as _select(), but standalone so that _select()
        can remain a regular function.

        """

        con = self._open()
        con.row_factory = sqlite3.Row

        with con:
            cur = con.cursor()
            cur.execute(query, values)
            while True:
                result = cur.fetchmany(size=arraysize)
                if not result:
                    break
                yield from result

    def _explain(self, query, values=()):
        """Get the query plan for a query."""

        return self._select(
            "EXPLAIN QUERY PLAN {}".format(query),
            values
        )

    @staticmethod
    def _cacheTable(query):
        """The name of the table that will cache results for the specified
        query.

        """

        checksum = cherrypy.engine.publish("checksum:string", query).pop()
        return "cache_{}".format(checksum)

    def _tableNames(self):
        """Get a list of tables in the database."""
        result = self._select(
            "SELECT name FROM sqlite_master WHERE type=?",
            ("table",)
        )
        return [row["name"] for row in result]

    def _dropCacheTables(self):
        """Remove all existing cache tables"""
        delete_queries = [
            ("DROP TABLE {}".format(table), ())
            for table in self._tableNames()
            if table.startswith("cache_")
        ]

        self._multi(delete_queries)

    def _selectToCache(self, query, values):
        """Send the results of a query to a cache table

        This is the sqlite way of doing "select into"
        """
        cache_table = self._cacheTable(query)

        con = self._open()
        with con:
            cur = con.cursor()

            # This delete is redundant with _dropCacheTables(), but it allows
            # a single cache to be cleaned up, instead of all of them.
            cur.execute("DROP TABLE IF EXISTS {}".format(cache_table))

            cur.execute(
                "CREATE TABLE {} AS {}".format(cache_table, query),
                values
            )

    def _selectOne(self, query, values=()):
        """Issue a select query and return the first row."""
        result = self._select(query, values)

        try:
            return result.pop()
        except IndexError:
            return {}

    def _selectFirst(self, query, values=()):
        """Issue a select query and return the first value of the first
        row.

        """

        result = self._select(query, values)

        try:
            row = result.pop()
            return row[0]
        except IndexError:
            return None
