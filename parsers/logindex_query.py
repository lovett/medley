"""Parser for logindex search queries."""

import calendar
from datetime import datetime
from datetime import timedelta
import re
from typing import Callable
from typing import Dict
from typing import Tuple
from pytz import UTC

Transformer = Callable[[str, str, bool], str]
PhraseTuple = Tuple[str, ...]
TermDict = Dict[str, PhraseTuple]


class Parser():
    """Convert a logindex search query to a SQL WHERE clause."""

    # A mapping between search keywords and the corresponding database column
    # that allows for aliasing.
    keywords = {
        "date": "datestamp",
        "source_file": "source_file",
        "ip": "ip",
        "host": "host",
        "uri": "uri",
        "query": "query",
        "status": "statusCode",
        "method": "method",
        "agent": "agent",
        "agent_domain": "agent_domain",
        "classification": "classification",
        "country": "country",
        "region": "region",
        "city": "city",
        "cookie": "cookie",
        "referrer": "referrer",
        "referrer_domain": "referrer_domain",
        "reverse_domain": "reverse_domain",
    }

    date_fields = ("datestamp",)
    numeric_fields = ("statusCode",)
    subquery_fields = ("reverse_domain",)

    def parse(self, query: str) -> str:
        """Convert a search query to an SQL phrase."""

        terms: TermDict = {}
        sql_phrases: PhraseTuple = ()
        field = None

        for word in query.lower().replace("\n", " ").split():
            if word in self.keywords:
                field = self.keywords[word]
                continue

            if not field:
                continue

            if field and word == "not":
                field = f"{field}_not"
                continue

            if field not in terms:
                terms[field] = (word,)
                continue

            terms[field] += (word,)

        if "datestamp" in terms:
            terms = self.qualify_terms(terms, "datestamp")

        for field, values in terms.items():
            sql_phrases += self.transform(
                field,
                values,
                self.get_transformer(field)
            )

        return " AND ".join(sql_phrases)

    @staticmethod
    def get_operator(term: str, negated: bool = False) -> str:
        """Identify the appropriate SQL comparison operator for a term."""

        operator = "="

        if negated:
            operator = "<>"

        if "%" in term:
            operator = "LIKE"
            if negated:
                operator = "NOT LIKE"

        return operator

    @staticmethod
    def non_negated_field(field: str) -> str:
        """Remove the negation suffix from a field."""

        if field.endswith("_not"):
            return field[:-4]

        return field

    def get_transformer(self, field: str) -> Transformer:
        """Match a field to a transform function."""

        field = self.non_negated_field(field).lstrip("+")

        if field in self.date_fields:
            return self.transform_date

        if field in self.numeric_fields:
            return self.transform_numeric

        if field in self.subquery_fields:
            return self.transform_subquery

        return self.transform_string

    @staticmethod
    def qualify_terms(terms: TermDict, index: str) -> TermDict:
        """Force the usage of a specific index.

        see Disqualifying WHERE Clause Terms Using Unary-"+" in
        https://www.sqlite.org/optoverview.html
        """

        qualified_terms: TermDict = {}
        for key, value in terms.items():
            if key == index:
                qualified_terms[key] = value
                continue

            qualified_terms[f"+{key}"] = value

        return qualified_terms

    def transform(
            self,
            field: str,
            terms: PhraseTuple,
            transformer: Transformer
    ) -> PhraseTuple:
        """Transform a set of values to an SQL phrase."""

        negated = False
        if field.endswith("_not"):
            negated = True
            field = self.non_negated_field(field)

        phrases = tuple(
            transformer(field, term, negated)
            for term in terms
        )

        boolean = " OR "
        if negated:
            boolean = " AND "
        return ("(" + boolean.join(phrases) + ")",)

    @staticmethod
    def transform_date(field: str, term: str, _: bool = False) -> str:
        """Convert a date value to an SQL phrase.

        Dates in YYYY-MM-DD and YYYY-MM format are recognized, as are
        the keywords "today" and "yesterday".

        """

        reference_date = None
        end_date_delta = timedelta(hours=23)

        if term == "today":
            reference_date = datetime.today()
        elif term == "yesterday":
            reference_date = datetime.today() - timedelta(days=1)
        elif re.match(r"\d{4}-\d{2}-\d{2}", term):
            reference_date = datetime.strptime(
                term,
                "%Y-%m-%d",
            )
        elif re.match(r"\d{4}-\d{2}", term):
            reference_date = datetime.strptime(
                term,
                "%Y-%m",
            )

            month_range = calendar.monthrange(
                reference_date.year,
                reference_date.month
            )

            end_date_delta = timedelta(days=month_range[1])

        if not reference_date:
            return ""

        start_date = reference_date.replace(
            hour=0, minute=0, second=0
        ).astimezone(UTC)

        end_date = start_date + end_date_delta

        start = start_date.strftime("%Y-%m-%d-%H")
        end = end_date.strftime("%Y-%m-%d-%H")

        return f"{field} BETWEEN '{start}' AND '{end}'"

    @staticmethod
    def transform_numeric(field: str, term: str, negated: bool = False) -> str:
        """Convert a numeric value to an SQL phrase."""

        operator = "="
        if negated:
            operator = "<>"

        return f"{field} {operator} {term}"

    def transform_string(
            self,
            field: str,
            term: str,
            negated: bool = False
    ) -> str:
        """Convert a string value to an SQL phrase."""

        # The IP field needs to be qualified because it is used
        # as the basis of a join. It is the only field that needs
        # this special handling.
        if field == "ip":
            field = "logs.ip"

        operator = self.get_operator(term, negated)

        return f"{field} {operator} '{term}'"

    def transform_subquery(
            self,
            field: str,
            term: str,
            _: bool = False
    ) -> str:
        """Build a SQL phrase that involves a subquery."""

        operator = self.get_operator(term, False)

        if field == "reverse_domain":
            return ("logs.ip IN ("
                    "SELECT ip "
                    "FROM reverse_ip "
                    f"WHERE reverse_domain {operator} '{term}')")

        return ""
