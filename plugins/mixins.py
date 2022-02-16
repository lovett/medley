"""Methods for issuing SQL queries against an SQLite database."""

import os.path
import sqlite3
from typing import Any
from typing import Iterator
from typing import List
from typing import Optional
from typing import Sequence
from typing import Tuple
from typing import Union
from typing import cast
import re
import cherrypy


# pylint: disable=invalid-name,no-member
class Sqlite:
    """Query an SQLite database using Python's DB-API."""

    db_path: str

    @staticmethod
    def _path(name: str) -> str:
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

    def _create(self, sql: str) -> None:
        """Establish a schema by executing a series of SQL statements."""

        con = self._open()

        try:
            with con:
                con.executescript(sql)
        except sqlite3.DatabaseError as err:
            self._logError(err)
        finally:
            con.close()

    def _execute(
            self,
            query: str,
            params: Sequence[Any] = ()
    ) -> bool:
        """Issue a single query."""

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

    def _multi(
            self,
            queries: Sequence[Tuple[str, Any]],
            after_commit: Tuple[str, Any] = None
    ) -> Union[bool, Iterator[sqlite3.Row]]:
        """Issue several queries within a transaction."""

        result = True
        con = self._open()
        con.isolation_level = None

        try:
            con.execute("BEGIN")
            for query, params in queries:
                con.execute(query, params)
            con.execute("COMMIT")

            if after_commit:
                return self._select_generator(
                    query=after_commit[0],
                    values=after_commit[1],
                    con=con
                )

            con.close()

        except sqlite3.DatabaseError as err:
            result = False
            self._logError(err)
            con.execute("rollback")
            con.close()

        return result

    def _delete(
            self,
            query: str,
            values: Sequence[Any] = ()
    ) -> int:
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

    def _count(
            self,
            query: str,
            values: Sequence[Any] = ()
    ) -> int:
        """Convert a select query to a count query and execute it."""

        count_query = re.sub(
            r"SELECT.*?(FROM.*)ORDER BY.*",
            r"SELECT count(*) \g<1>",
            query,
            flags=re.MULTILINE | re.DOTALL | re.IGNORECASE
        )

        placeholder_count = count_query.count("?")
        placeholder_values = values[0:placeholder_count]

        return cast(
            int,
            self._selectFirst(
                count_query,
                placeholder_values
            )
        )

    def _select(
            self,
            query: str,
            values: Sequence[Any] = ()
    ) -> List[sqlite3.Row]:
        """Execute a select query."""

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
            values: Sequence[Any] = (),
            con: Optional[sqlite3.Connection] = None
    ) -> Iterator[sqlite3.Row]:
        """Execute a select query and return results as a generator."""

        if not con:
            con = self._open()

        con.row_factory = sqlite3.Row

        try:
            yield from con.execute(query, values)
        except sqlite3.DatabaseError as err:
            self._logError(err)
        finally:
            con.close()

    def _explain(
            self,
            query: str,
            values: Sequence[Any] = ()
    ) -> List[str]:
        """Get the query plan for a query."""

        generator = self._select_generator(
            f"EXPLAIN QUERY PLAN {query}",
            values
        )

        result = []
        for row in generator:
            prefix = ""
            if row["parent"] > 0:
                prefix = "-- "
            result.append(f"{prefix}{row['detail']}")

        return result

    def _selectOne(
            self,
            query: str,
            values: Sequence[Any] = ()
    ) -> Optional[sqlite3.Row]:
        """Issue a select query and return the first row."""

        row = None
        con = self._open()
        con.row_factory = sqlite3.Row

        try:
            for row in con.execute(query, values):
                break
        except sqlite3.DatabaseError as err:
            self._logError(err)
        finally:
            con.close()

        return row

    def _selectFirst(
            self,
            query: str,
            values: Sequence[Any] = ()
    ) -> Any:
        """Issue a select query and return the first value of the first
        row.

        """

        result = self._selectOne(query, values)
        if result:
            return result[0]
        return None

    def _logError(self, err: sqlite3.DatabaseError) -> None:
        """Write database exceptions to the cherrypy log."""

        db_name = os.path.basename(self.db_path)
        cherrypy.log(f"ERROR: {db_name} {err}")
