"""Parser for logindex search queries."""

import re
import typing
import pendulum

Transformer = typing.Callable[[str, str, bool], str]
PhraseTuple = typing.Tuple[str, ...]
TermDict = typing.Dict[str, PhraseTuple]


class Parser():
    """Convert a logindex search query to a SQL WHERE clause."""

    timezone: str

    # A mapping between search keywords and the corresponding database column
    # that allows for aliasing.
    keywords = {
        "date": "datestamp",
        "datestamp": "datestamp",
        "source_file": "source_file",
        "ip": "ip",
        "host": "host",
        "uri": "uri",
        "query": "query",
        "statuscode": "statusCode",
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
    subquery_fields = ("reverse_domain")

    def parse(self, query: str, timezone: str) -> str:
        """Convert a search query to an SQL phrase."""

        self.timezone = timezone

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

        field = self.non_negated_field(field)

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

    def transform_date(self, field: str, term: str, _: bool = False) -> str:
        """Convert a date value to an SQL phrase.

        Dates in YYYY-MM-DD and YYYY-MM format are recognized, as are
        the keywords "today" and "yesterday".

        """

        reference_date = None

        if term == "today":
            reference_date = pendulum.today()
        elif term == "yesterday":
            reference_date = pendulum.yesterday()
        elif re.match(r"\d{4}-\d{2}-\d{2}", term):
            reference_date = pendulum.from_format(
                term,
                "YYYY-MM-DD",
                tz=self.timezone
            )
        elif re.match(r"\d{4}-\d{2}", term):
            reference_date = pendulum.from_format(
                term,
                "YYYY-MM",
                tz=self.timezone
            )

        if not reference_date:
            return ""

        start = reference_date.start_of("day").in_timezone("utc").format(
            "YYYY-MM-DD-HH"
        )

        end = reference_date.end_of("day").in_timezone("utc").format(
            "YYYY-MM-DD-HH"
        )

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
