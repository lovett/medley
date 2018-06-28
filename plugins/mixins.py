"""Methods for issuing SQL queries against an SQLite database."""

import os.path
import sqlite3
from itertools import zip_longest
import cherrypy


# pylint: disable=invalid-name
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
        """Issue create table statements when a new database is created."""

        if os.path.isfile(self.db_path):
            return

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

    def _delete(self, query, values):
        """Issue a delete query."""
        con = self._open()
        with con:
            row_count = con.execute(query, values).rowcount
        con.close()
        return row_count

    def _select(self, query, values=()):
        """Issue a select query."""
        con = self._open()
        con.row_factory = sqlite3.Row

        with con:
            cur = con.cursor()
            cur.execute(query, values)
            return cur.fetchall() or []

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

    @staticmethod
    def _fts_rank(match_info, *weights):
        """Sqlite user function for search ranking

        This is based on an example C provided in the SQLite
        documentation.

        The SQL query is expected to call matchinfo with the default
        format string, "pcx".

        Returns a float representing the combined relevance of all
        terms across all fulltext columns. The larger the value, the
        higher the relevance.

        see http://www.sqlite.org/fts3.html#appendix_a

        """

        view = memoryview(match_info).cast('@I')

        # Value corresponding to the p character of the matchinfo format
        # string. A single value.
        phrase_count = view[0]

        # Value corresponding to the c character of the matchinfo
        # format string. A single value.
        column_count = view[1]

        # Value corresponding to the x character of matchinfo format
        # string. A trio of values per phrase and column as one list.
        # End of slice adds 2 to account for phrase and column count.
        hits = view[2:(phrase_count * column_count * 3 + 2)]

        # Chunk the list.
        # see https://docs.python.org/3.5/library/itertools.html
        hit_triples = zip_longest(*[iter(hits)] * 3, fillvalue=999999)

        score = 0.0

        for triple_index, triple in enumerate(hit_triples):
            # How many times phrase X matched in column Y of record Z.
            hits_this_row = triple[0]

            # How many times phrase X matched in column Y of all records.
            hits_all_rows = triple[1]

            # How many records phrase X matched in column Y of all records.
            # docs_with_hits = triple[2]

            if hits_all_rows == 0:
                continue

            weight = weights[triple_index % len(weights)]
            score += (hits_this_row / hits_all_rows) * weight

        return score

    def _fts_search(self, query, values=()):
        """Issue a fulltext search query."""

        con = self._open()
        con.row_factory = sqlite3.Row

        con.create_function("rank", -1, self._fts_rank)

        with con:
            cur = con.cursor()
            cur.execute(query, values)
            return cur.fetchall() or []
