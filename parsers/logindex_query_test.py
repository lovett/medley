"""Test suite for the logindex_query parser."""

import unittest
import parsers.logindex_query


class TestLogindexQueryParser(unittest.TestCase):
    """Tests for the logindex_query parser."""

    parser: parsers.logindex_query.Parser

    @classmethod
    def setUpClass(cls) -> None:
        """Create the parser instance."""
        cls.parser = parsers.logindex_query.Parser()

    def parse_and_assert(self, query: str, expected: str) -> None:
        """Submit a query to the parser and assert its result."""

        result = self.parser.parse(query)
        self.assertEqual(result, expected)

    def test_invalid_keyword(self) -> None:
        """A query with no keywords is ignored."""
        query = "invalid 2020-12-12"
        expected = ""

        self.parse_and_assert(query, expected)

    def test_date(self) -> None:
        """Searching for a date produces a BETWEEN range in UTC."""

        query = "date 2020-01-01"
        expected = "(datestamp BETWEEN '2020-01-01-05' AND '2020-01-02-04')"

        self.parse_and_assert(query, expected)

        query = "date 2020-02-01 2020-02-02"
        expected = ("("
                    "datestamp BETWEEN '2020-02-01-05' AND '2020-02-02-04' "
                    "OR "
                    "datestamp BETWEEN '2020-02-02-05' AND '2020-02-03-04'"
                    ")")

        self.parse_and_assert(query, expected)

    def test_numeric(self) -> None:
        """Searching for a numeric value does not quote unnecessarily."""

        query = "status 404"
        expected = "(statusCode = 404)"

        self.parse_and_assert(query, expected)

        query = "status 500 501"
        expected = "(statusCode = 500 OR statusCode = 501)"

        self.parse_and_assert(query, expected)

        query = "status not 400 410"
        expected = "(statusCode <> 400 AND statusCode <> 410)"

        self.parse_and_assert(query, expected)

        query = "date 2000-01-01 status 200"
        expected = (
            "(datestamp BETWEEN '2000-01-01-05' AND '2000-01-02-04') "
            "AND (+statusCode = 200)"
        )

        self.parse_and_assert(query, expected)

    def test_string(self) -> None:
        """Searching for a string value applies quotign."""

        query = "ip 1.2.3.4"
        expected = "(logs.ip = '1.2.3.4')"

        self.parse_and_assert(query, expected)

        query = "ip 1.1.1.1 2.2.%"
        expected = "(logs.ip = '1.1.1.1' OR logs.ip LIKE '2.2.%')"

        self.parse_and_assert(query, expected)

        query = "ip not 3.3.3.3 4.4.%"
        expected = "(logs.ip <> '3.3.3.3' AND logs.ip NOT LIKE '4.4.%')"

        self.parse_and_assert(query, expected)

    def test_subquery(self) -> None:
        """Searching for a value in a secondary table uses a subquery."""

        query = "reverse_domain reverse.example.com"
        expected = ("("
                    "logs.ip IN ("
                    "SELECT ip FROM reverse_ip "
                    "WHERE reverse_domain = 'reverse.example.com'"
                    "))")

        self.parse_and_assert(query, expected)

        query = "reverse_domain %.example.com"
        expected = ("("
                    "logs.ip IN ("
                    "SELECT ip FROM reverse_ip "
                    "WHERE reverse_domain LIKE '%.example.com'"
                    "))")

        self.parse_and_assert(query, expected)

    def test_mixed_negation(self) -> None:
        """Queries can specify wanted and unwanted terms for the same field."""

        query = "uri /hello% uri not /unwanted"

        expected = ("(uri LIKE '/hello%')"
                    " AND "
                    "(uri <> '/unwanted')")

        self.parse_and_assert(query, expected)


if __name__ == "__main__":
    unittest.main()
