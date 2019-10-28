"""Methods for issuing SQL queries against an SQLite database."""

import os.path
import sqlite3
import typing
import re
from typing import Any, List, Tuple, Optional, Union
import cherrypy


# pylint: disable=invalid-name,no-member
class Sqlite:
    """Query an SQLite database using Python's DB-API."""

    db_path: typing.Optional[str] = None

    @staticmethod
    def _path(name):
        """Get the filesystem path of a database file relative to the
        application database directory.

        """

        return os.path.join(
            cherrypy.config.get("database_dir", "db"),
            name
        )

    def _open(self) -> sqlite3.Connection:
        """Open a connection to the current database."""

        return sqlite3.connect(
            self.db_path,
            detect_types=sqlite3.PARSE_COLNAMES
        )

    def _create(self, sql) -> bool:
        """Establish a schema by executing a series of SQL statements.

        The statements should be re-runnable so that new objects will
        be created automatically. This can be accomplished with "IF
        NOT EXISTS" statements when creating tables and triggers.

        This approach is geared toward new objects. It won't account
        for modifications to existing objects such as ALTER TABLE.

        """

        result = True
        con = self._open()

        try:
            with con:
                con.executescript(sql)
        except sqlite3.DatabaseError as err:
            result = False
            self._logError(err)
        finally:
            con.close()

        return result

    def _execute(self, query, params=()) -> bool:
        """Execute a single query with no parameters."""

        result = True
        con = self._open()

        try:
            with con:
                con.execute(query, params)
        except sqlite3.DatabaseError as err:
            result = False
            self._logError(err)
        finally:
            con.close()

        return result

    def _multi(self, queries) -> bool:
        """Issue several queries."""

        result = True
        con = self._open()

        try:
            with con:
                for query, params in queries:
                    con.execute(query, params)
        except sqlite3.DatabaseError as err:
            result = False
            self._logError(err)
        finally:
            con.close()

        return result

    def _insert(self, query, values) -> bool:
        """Issue an insert query to create one or more records.

        Cannot return lastrowid because it is not populated
        during executemany().
        """

        result = True
        con = self._open()

        try:
            with con:
                con.executemany(query, values)
        except sqlite3.DatabaseError as err:
            result = False
            self._logError(err)
        finally:
            con.close()

        return result

    def _update(self, query, values) -> bool:
        """Issue an update query."""

        result = True
        con = self._open()

        try:
            with con:
                con.executemany(query, values)
        except sqlite3.DatabaseError as err:
            result = False
            self._logError(err)
        finally:
            con.close()

        return result

    def _delete(self, query: str, values: Tuple[Any] = ()) -> int:
        """Issue a delete query."""

        result = 0
        con = self._open()

        try:
            with con:
                result = con.execute(query, values).rowcount
        except sqlite3.DatabaseError as err:
            result = 0
            self._logError(err)
        finally:
            con.close()

        return result

    def _count(self, query, values=()) -> int:
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

    def _select(self, query, values=()) -> List[sqlite3.Row]:
        """Issue a select query."""

        result = None
        con = self._open()
        con.row_factory = sqlite3.Row
        cur = con.cursor()

        try:
            with con:
                cur.execute(query, values)
                result = cur.fetchall() or []
        except sqlite3.DatabaseError as err:
            result = []
            self._logError(err)
        finally:
            con.close()

        return result

    def _select_generator(
            self,
            query: str,
            values: typing.Tuple[typing.Any, ...] = (),
            arraysize: int = 1
    ) -> typing.Iterator[sqlite3.Row]:
        """Issue a select query and return results as a generator.

        Nearly the same as _select(), but standalone so that _select()
        can remain a regular function.

        """

        con = self._open()
        con.row_factory = sqlite3.Row
        cur = con.cursor()

        try:
            cur.execute(query, values)
        except sqlite3.DatabaseError as err:
            con.close()
            self._logError(err)
            return None

        while True:
            result = cur.fetchmany(size=arraysize)
            if not result:
                con.close()
                break
            yield from result

    def _explain(self, query, values=()) -> sqlite3.Row:
        """Get the query plan for a query."""

        return self._select(
            f"EXPLAIN QUERY PLAN {query}",
            values
        )

    @staticmethod
    def _cacheTable(query):
        """The name of the table that will cache results for the specified
        query.

        """

        checksum = cherrypy.engine.publish("checksum:string", query).pop()
        return f"cache_{checksum}"

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
            (f"DROP TABLE {table}", ())
            for table in self._tableNames()
            if table.startswith("cache_")
        ]

        self._multi(delete_queries)

    def _selectOne(self, query, values=()) -> Union[sqlite3.Row, None]:
        """Issue a select query and return the first row."""
        result = self._select(query, values)

        try:
            return result.pop()
        except IndexError:
            return None

    def _selectFirst(self, query, values=()) -> Optional[sqlite3.Row]:
        """Issue a select query and return the first value of the first
        row.

        """

        result = self._select(query, values)

        try:
            row = result.pop()
            return row[0]
        except IndexError:
            return None

    def _logError(self, err: sqlite3.DatabaseError) -> None:
        """Write database exceptions to the cherrypy log."""

        db_name = os.path.basename(self.db_path)
        cherrypy.log(f"ERROR: {db_name} {err}")
