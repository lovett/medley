"""Grammar-based parsing using pyparsing."""

import string
from urllib.parse import urlparse
import pyparsing as pp
import cherrypy
import pendulum


class Plugin(cherrypy.process.plugins.SimplePlugin):
    """A CherryPy plugin for interacting with pyparsing grammars."""

    def __init__(self, bus):
        cherrypy.process.plugins.SimplePlugin.__init__(self, bus)

        # Parsing primitives
        integer = pp.Word(pp.nums)

        ipv4 = pp.Combine(
            integer + "." + integer + "." + integer + "." + integer
        )

        ipv6 = pp.Word(pp.alphanums + ":")

        month3 = pp.Word(
            string.ascii_uppercase,
            string.ascii_lowercase,
            exact=3
        )

        date10 = pp.Group(
            pp.Word(pp.nums, exact=4) + pp.Suppress("-") +
            pp.Word(pp.nums, exact=2) + pp.Suppress("-") +
            pp.Word(pp.nums, exact=2)
        )

        date7 = pp.Group(
            pp.Word(pp.nums, exact=4) + pp.Suppress("-") +
            pp.Word(pp.nums, exact=2)
        )

        tzoffset = pp.Word("+-", pp.nums)

        timestamp = pp.Group(
            pp.Suppress("[") +
            pp.MatchFirst([
                pp.Combine(
                    integer + "/" + month3 + "/" + integer + ":" +
                    integer + ":" + integer + ":" + integer +
                    " " + tzoffset
                ),
                pp.Combine(
                    integer + "/" + month3 + "/" + integer + ":" +
                    integer + ":" + integer + ":" + integer + ":" + integer +
                    " " + tzoffset
                )
            ]) +
            pp.Suppress("]")
        )

        optional_not = pp.Optional(pp.Literal("not"))

        # Appengine Combined Log Grammar
        # Field order is documented at:
        # https://cloud.google.com/appengine/docs/python/logs/
        #
        # This is heavily based on:
        # http://pyparsing.wikispaces.com/file/view/httpServerLogParser.py/30166005/httpServerLogParser.py

        # ip
        appengine_fields = (ipv4 | ipv6).setResultsName("ip")

        # ident
        appengine_fields += pp.Suppress("-")

        # auth
        appengine_fields += (
            "-" |
            pp.dblQuotedString |
            pp.Word(pp.alphanums + "@._")
        ).setParseAction(self.dash_to_none)

        # timestamp
        appengine_fields += timestamp.setResultsName(
            "timestamp"
        ).setParseAction(
            self.first_in_group
        ).setResultsName("timestamp")

        # cmd
        appengine_fields += pp.dblQuotedString.setParseAction(
            self.request_fields
        ).setResultsName("cmd")

        # status
        appengine_fields += ("-" | integer).setParseAction(
            self.dash_to_none
        ).setResultsName("statusCode")

        # bytes sent
        appengine_fields += ("-" | integer).setParseAction(
            self.dash_to_none
        ).setResultsName("numBytesSent")

        # referrer
        appengine_fields += ("-" | pp.dblQuotedString).setParseAction(
            pp.removeQuotes,
            self.dash_to_none
        ).setResultsName("referrer")

        # agent
        appengine_fields += ("-" | pp.dblQuotedString).setParseAction(
            pp.removeQuotes,
            self.dash_to_none
        ).setResultsName("agent")

        # host
        appengine_fields += pp.Optional(
            pp.dblQuotedString.setParseAction(pp.removeQuotes)
        ).setResultsName("host")

        # extras
        appengine_fields += pp.Optional(
            pp.dictOf(
                pp.Word(pp.alphanums + "_") +
                pp.Suppress("="),
                pp.dblQuotedString
            ).setParseAction(
                self.to_dict
            ).setResultsName("extras")
        )

        self.appengine_grammar = appengine_fields

        # Custom grammar for querying the logindex database
        # Converts a list key-value pairs to SQL

        self.logquery_grammar = pp.delimitedList(
            pp.Or([
                # relative date
                (
                    pp.Literal("date") +
                    pp.oneOf("today yesterday")
                ).setParseAction(self.log_query_relative_date),

                # absolute date in yyyy-mm-dd or yyyy-mm format
                (
                    pp.Literal("date") +
                    pp.OneOrMore(date10 | date7)
                ).setParseAction(self.log_query_absolute_date),

                # numeric fields
                (
                    pp.oneOf("statusCode") +
                    optional_not +
                    pp.OneOrMore(integer)
                ).setParseAction(self.log_query_numeric),

                # url
                (
                    pp.oneOf("""
                    uri
                    ip
                    """) +
                    optional_not +
                    pp.OneOrMore(pp.Word(pp.alphanums + "%/-.:"))
                ).setParseAction(self.log_query_wildcard),

                # string fields
                (
                    pp.oneOf("""
                    city
                    country
                    region
                    classification
                    method
                    cookie
                    uri
                    agent_domain
                    classification
                    referrer_domain""") +
                    optional_not +
                    pp.OneOrMore(pp.Word(pp.alphanums + ".-"))
                ).setParseAction(self.log_query_exact_string),

                # string field involving a subquery
                (
                    pp.oneOf("""
                    reverse_domain
                    """) +
                    pp.OneOrMore(pp.Word(pp.alphanums + ".-"))
                ).setParseAction(self.log_query_subquery),
            ]),
            "|"
        )

    def start(self):
        """Define the CherryPy messages to listen for.

        This plugin owns the parse prefix.
        """

        self.bus.subscribe('parse:appengine', self.parse_appengine)
        self.bus.subscribe('parse:log_query', self.parse_log_query)

    @staticmethod
    def request_fields(_string, _location, tokens):
        """Subdivide the cmd field to isolate method, uri, query, and version

        Extra care needs to be taken because the uri could contain
        unexpected garbage. Just splitting on whitespace is too
        brittle, even though it's the straightforward approach that
        works for the normal case."""

        fields = tokens[0].strip('"').split()

        uri = ' '.join(fields[1:-1])

        tokens["method"] = fields[0]
        tokens["uri"] = uri
        tokens["query"] = None
        tokens["version"] = fields[-1]
        if "?" in uri:
            tokens["uri"], tokens["query"] = tokens["uri"].split('?', 1)

    @staticmethod
    def first_in_group(_string, _location, tokens):
        """Return the first item in a group."""
        return tokens[0][0]

    @staticmethod
    def dash_to_none(_string, _location, tokens):
        """Coerce a bare hypen to None"""
        if tokens[0] == "-":
            return None

        return tokens[0]

    @staticmethod
    def log_query_relative_date(_string, _location, tokens):
        """Generate an SQL where clause for a date expressed via keyword.

        Recognized keywords are "today" and "yesterday".

        The SQL describes a range rather than a fixed day to account
        for timezone differences between the query and the source
        data. For example, "today" in local time is more like "today
        and a bit of tomorrow" in UTC.

        For performance, the query is structured to take advantage of
        an expression-based index. This only works when the query expression
        matches the expression used in the create index statement.
        """

        if tokens[1] == "today":
            reference_date = pendulum.today()
        elif tokens[1] == "yesterday":
            reference_date = pendulum.yesterday()

        sql_start = reference_date.start_of('day').in_timezone('utc').format(
            'YYYY-MM-DD-HH'
        )

        sql_end = reference_date.end_of('day').in_timezone('utc').format(
            'YYYY-MM-DD-HH'
        )

        return f"datestamp BETWEEN '{sql_start}' AND '{sql_end}'"

    @staticmethod
    def log_query_absolute_date(_string, _location, tokens):
        """Generate an SQL where clause for a date expressed literally.

        Dates can either be in YYYY-mm or YYYY-mm-dd format.

        The SQL describes a range rather than a fixed day to account
        for timezone differences between the query and the source
        data. For example, a given date in local time also extends
        into the following day (or prior day) when converted to UTC.

        For performance, the query is structured to take advantage of
        an expression-based index. This only works when the query expression
        matches the expression used in the create index statement.
        """

        dates = tokens[1:]
        date_interval = "day"

        timezone = cherrypy.engine.publish(
            "registry:first_value",
            "config:timezone",
            memorize=True
        ).pop()

        if not timezone:
            timezone = pendulum.now().timezone.name

        sql = []

        for date in dates:
            ints = tuple(map(int, date))
            if len(date) == 2:
                date_interval = "month"
                year, month = ints
                day = 1

            if len(date) == 3:
                year, month, day = ints

            reference_date = pendulum.datetime(year, month, day, tz=timezone)

            sql_start = reference_date.start_of(
                date_interval
            ).in_timezone("utc").format("YYYY-MM-DD-HH")

            sql_end = reference_date.end_of(
                date_interval
            ).in_timezone("utc").format("YYYY-MM-DD-HH")

            sql.append(f"datestamp BETWEEN '{sql_start}' AND '{sql_end}'")

        sql = " OR ".join(sql)
        return f"({sql})"

    @staticmethod
    def log_query_numeric(_string, _location, tokens):
        """Build an SQL string for a numeric comparison."""

        field = tokens[0]

        if tokens[1] == "not":
            values = tokens[2:]
            sql = [f"{field} <> {value}" for value in values]
            joined_sql = " AND ".join(sql)
        else:
            values = tokens[1:]
            sql = [f"{field} = {value}" for value in values]
            joined_sql = " OR ".join(sql)

        return f"({joined_sql})"

    @staticmethod
    def log_query_wildcard(_string, _location, tokens):
        """Build an SQL string for a wildcard comparison."""
        field = tokens[0]

        if tokens[1] == "not":
            values = tokens[2:]
            wildcard_operator = "NOT LIKE"
            equality_operator = "<>"
            boolean_keyword = " AND "
        else:
            values = tokens[1:]
            wildcard_operator = "LIKE"
            equality_operator = "="
            boolean_keyword = " OR "

        sql = []
        for value in values:
            if value.startswith("%") or value.endswith("%"):
                sql.append(f"{field} {wildcard_operator} '{value}'")
            else:
                sql.append(f"{field} {equality_operator} '{value}'")

        return f"({boolean_keyword.join(sql)})"

    @staticmethod
    def log_query_subquery(_string, _location, tokens):
        """Build an SQL where clause fragment for a field lookup that involves
        a subquery.

        """

        field = tokens[0]

        sql = ""
        if field == "reverse_domain":
            values = [f"'{value}'" for value in tokens[1:]]
            sql = f"""logs.ip IN (
                SELECT ip
                FROM reverse_ip
                WHERE reverse_domain
                IN ({','.join(values)}))"""  # nosec

        return sql

    @staticmethod
    def log_query_exact_string(_string, _location, tokens):
        """Build an SQL string for an exact string comparison."""

        field = tokens[0]

        # The IP field needs to be qualified because it is used
        # as the basis of a join. It is the only field that needs
        # this special handling.
        if field == "ip":
            field = "logs.ip"

        if tokens[1] == "not":
            values = tokens[2:]
            sql = [f"{field} <> '{value}'" for value in values]
            joined_sql = " AND ".join(sql)
        else:
            values = tokens[1:]
            sql = [f"{field} = '{value}'" for value in values]
            joined_sql = " OR ".join(sql)

        return f"({joined_sql})"

    @staticmethod
    def to_dict(_string, _location, tokens):
        """Apply the keys and values returned by pyparsing.dictOf to the main
        parse result

        """
        result = {}
        for key, val, in tokens[0].items():
            if val.startswith('"') and val.endswith('"'):
                result[key] = val[1:-1]
            else:
                result[key] = val

        return result

    def parse_appengine(self, val):
        """Parse a log line in combined-plus-Appengine-extras format

        App Engine extras consist of additional key=value pairs after
        the ones for the combined format. This is where
        App Engine-sourced geoip values are found. It also contains
        less interesting things like the instance ID that served the
        request."""

        # Sanity check to make sure double-quoted fields are balanced.
        val = val.strip()
        if val.count('"') % 2 > 0:
            val = f'{val}"'

        # Sanity check to avoid problems with an empty double-quoted
        # string for the referrer field.
        val = val.replace(' "" "', ' - "')

        try:
            fields = self.appengine_grammar.parseString(val).asDict()
        except pp.ParseException as exception:
            cherrypy.engine.publish(
                "applog:add",
                "parse",
                f"fail:column:{exception.col}",
                val
            )

        timestamp_formats = (
            "DD/MMM/YYYY:HH:mm:ss ZZ",
            "DD/MMM/YYYY:HH:mm:ss:SSSSSS ZZ"
        )

        for timestamp_format in timestamp_formats:
            try:
                utc_time = pendulum.from_format(
                    fields["timestamp"],
                    timestamp_format
                ).in_tz('utc')
                break
            except ValueError:
                pass

        fields["unix_timestamp"] = utc_time.timestamp()
        fields["datestamp"] = utc_time.format("YYYY-MM-DD-HH")

        if "referrer" in fields:
            parse_result = urlparse(fields["referrer"])

            # Ignore netloc if it is an empty string.
            if parse_result.netloc:
                fields["referrer_domain"] = parse_result.netloc

        for key, value in fields["extras"].items():
            if value in ("ZZ", "?", ""):
                continue

            if key == "country":
                fields[key] = value.upper()
                continue

            if key == "city":
                fields[key] = value.title()
                continue

            if key == "region" and len(value) == 2:
                fields[key] = value.upper()
                continue

            if key == "latlong" and "," in value:
                fields["latitude"], fields["longitude"] = value.split(",")
                continue

            fields[key] = value

        del fields["extras"]
        return fields

    def parse_log_query(self, val):
        """Convert a logindex query to sql

        The query is used to build the WHERE clause of an SQL query,
        which is otherwise built within the logindex plugin. The
        parsing that occurs here deals with things like exact and
        wildcard matching, multiple values for the same field, and
        basic boolean logic.

        The query is expected to be a multi-line string containing
        space-separated field names and search values.

        """

        val = val.replace("\r", "").strip().replace("\n", "|")

        result = self.logquery_grammar.parseString(val).asList()

        # Force usage of the datestamp index.
        #
        # A query with multiple criteria might otherwise be mis-optimized
        # by sqlite and use an index that is less performant. Prefixing columns
        # with "+" prevents the term from influencing index choice.
        #
        # In the majority of cases, queries will be date-limited and
        # the datestamp index is the better choice.
        #
        # see https://www.sqlite.org/optoverview.html

        if any(("datestamp" in item for item in result)):
            result = tuple(
                item.replace("(", "(+") if "datestamp" not in item
                and "reverse_domain" not in item
                else item
                for item in result
            )

        sql = " AND ".join(result)

        return sql
