import cherrypy
import os
from cherrypy.process import plugins
from collections import defaultdict
from pyparsing import *
import string
import os.path
from urllib.parse import urlparse
from datetime import datetime, timedelta

# Parse action helper methods receive 3 arguments:
# s is the original parse string
# l is the location in the string where matching started
# t is the list of the matched tokens, packaged as a ParseResults_ object
class Plugin(plugins.SimplePlugin):
    def __init__(self, bus):
        plugins.SimplePlugin.__init__(self, bus)

        # Parsing primitives
        self.integer = Word(nums)
        self.ipv4 = Combine(self.integer + "." + self.integer + "." + self.integer + "." + self.integer)
        self.ipv6 = Word(alphanums + ":")
        self.month3 = Word(string.ascii_uppercase, string.ascii_lowercase, exact=3)

        self.date10 = Group(
            Word(nums, exact=4) + Suppress("-") +
            Word(nums, exact=2) + Suppress("-") +
            Word(nums, exact=2)
        )

        self.date7 = Group(
             Word(nums, exact=4) + Suppress("-") +
             Word(nums, exact=2) + Suppress("-")
        )

        self.tzoffset = Word("+-", nums)
        self.timestamp = Group(
            Suppress("[") +
            Combine(
                self.integer + "/" + self.month3 + "/" + self.integer +
                ":" + self.integer + ":" + self.integer + ":" + self.integer +
                " " + self.tzoffset
            ) +
            Suppress("]")
        )

        self.optionalNot = Optional(Literal("not"))

        # Appengine Combined Log Grammar
        # Field order is documented at https://cloud.google.com/appengine/docs/python/logs/#Python_how_to_read_a_log
        # This is heavily based on  http://pyparsing.wikispaces.com/file/view/httpServerLogParser.py/30166005/httpServerLogParser.py
        self.appengine_grammar = (self.ipv4 | self.ipv6).setResultsName("ip") + \
        Suppress("-") + \
        ("-" | Word( alphanums + "@._")).setResultsName("auth").setParseAction(self.dashToNone) + \
        self.timestamp.setResultsName("timestamp").setParseAction(self.firstInGroup) + \
        dblQuotedString.setResultsName("cmd").setParseAction(self.requestFields) + \
        ("-" | self.integer).setResultsName("statusCode").setParseAction(self.dashToNone) + \
        ("-" | self.integer).setResultsName("numBytesSent").setParseAction(self.dashToNone) + \
        ("-" | dblQuotedString).setResultsName("referrer").setParseAction(removeQuotes, self.dashToNone) + \
        ("-" | dblQuotedString).setResultsName("agent").setParseAction(removeQuotes, self.dashToNone) + \
        Optional(dblQuotedString.setResultsName("host").setParseAction(removeQuotes)) + \
        Optional(dictOf(Word(alphanums + "_") + Suppress("="), dblQuotedString).setResultsName("extras").setParseAction(self.toDict))

        # Custom grammar for querying the logindex database
        # Converts a list key-value pairs to SQL
        self.logquery_grammar = delimitedList(
            Or([
                # relative date
                (Literal("date") + oneOf("today yesterday")).setParseAction(self.logQueryRelativeDate),

                # absolute date in yyyy-mm-dd or yyyy-mm format
                (Literal("date") + OneOrMore(self.date10 | self.date7)).setParseAction(self.logQueryAbsoluteDate),

                # numeric fields
                (oneOf("year month day hour statusCode") +
                 self.optionalNot +
                 OneOrMore(self.integer)).setParseAction(self.logQueryNumeric),

                # url
                (Literal("uri") + self.optionalNot + OneOrMore(Word(alphanums + "%/-."))).setParseAction(self.logQueryWildcard),

                # string fields
                (oneOf("city country region postal_code classification method cookie uri agent_domain classification reverse_domain referrer_domain") +
                 self.optionalNot +
                 OneOrMore(Word(alphanums + ".-"))).setParseAction(self.logQueryExactString),

                # ip
                (Literal("ip") + self.optionalNot + OneOrMore(self.ipv4 | self.ipv6)).setParseAction(self.logQueryExactString)

            ]),
            "|"
        )

    def start(self):
        self.bus.subscribe('parse:appengine', self.parseAppengine)
        self.bus.subscribe('parse:log_query', self.parseLogQuery)

    def stop(self):
        pass

    def requestFields(self, s, l, t):
        """Subdivide the cmd field to isolate method, uri, query, and version"""
        method, uri, version = t[0].strip('"').split()

        t["method"] = method
        t["uri"] = uri
        t["query"] = None
        t["version"] = version
        if "?" in uri:
            t["uri"], t["query"] = uri.split('?', 1)


    def firstInGroup(self, s, l, t):
        return t[0][0]

    def dashToNone(self, s, l, t):
        """Coerce a bare hypen to None"""
        return None if t[0] == "-" else t[0]


    def logQueryRelativeDate(self, s, l, t):
        if t[1] == "today":
            d = datetime.now()
        elif t[1] == "yesterday":
            d = datetime.now() - timedelta(days=1)

        return "year={} AND month={} AND day={}".format(d.year, d.month, d.day)


    def logQueryAbsoluteDate(self, s, l, t):
        field = t[0]

        dates = t[1:]

        sql = []
        for date in dates:
            year = int(date[0])
            month = int(date[1])

            if len(date) == 2:
                sql.append("(year={} AND month={})".format(year, month))

            if len(date) == 3:
                day = int(date[2])
                sql.append("(year={} AND month={} AND day={})".format(year, month, day))

        joined_sql = " OR ".join(sql)
        return "({})".format(joined_sql)


    def logQueryNumeric(self, s, l, t):
        field = t[0]

        if t[1] == "not":
            values = t[2:]
            sql = ["{} <> {}".format(field, value) for value in values]
            joined_sql = " AND ".join(sql)
        else:
            values = t[1:]
            sql = ["{} = {}".format(field, value) for value in values]
            joined_sql = " OR ".join(sql)

        return "({})".format(joined_sql)

    def logQueryWildcard(self, s, l, t):
        field = t[0]

        if t[1] == "not":
            values = t[2:]
            wildcard_operator = "NOT LIKE"
            equality_operator = "<>"
            boolean_keyword = " AND "
        else:
            values = t[1:]
            wildcard_operator = "LIKE"
            equality_operator = "="
            boolean_keyword = " OR "

        sql = []
        for value in values:
            if value.startswith("%") or value.endswith("%"):
                sql.append("{} {} '{}'".format(field, wildcard_operator, value))
            else:
                sql.append("{} {} '{}'".format(field, equality_operator, value))

        joined_sql = boolean_keyword.join(sql)
        return "({})".format(joined_sql)

    def logQueryExactString(self, s, l, t):
        field = t[0]

        # The IP field needs to be qualified because it is used
        # as the basis of a join. It is the only field that needs
        # this special handling.
        if field == "ip":
            field = "logs.ip"

        if t[1] == "not":
            values = t[2:]
            sql = ["{} <> '{}'".format(field, value) for value in values]
            joined_sql = " AND ".join(sql)
        else:
            values = t[1:]
            sql = ["{} = '{}'".format(field, value) for value in values]
            joined_sql = " OR ".join(sql)

        return "({})".format(joined_sql)

    def toDict(self, s, l, t):
        """Apply the keys and values returned by pyparsing.dictOf to the main parse result"""
        d = {}
        for k, v, in t[0].items():
            if v.startswith('"') and v.endswith('"'):
                d[k] = v[1:-1]
            else:
                d[k] = v

        return d

    def parseAppengine(self, val):
        """Convert a combined format log line with Appengine extra fields into a dict"""
        fields = self.appengine_grammar.parseString(val.strip()).asDict()
        fields["timestamp"] = datetime.strptime(fields["timestamp"], "%d/%b/%Y:%H:%M:%S %z")
        fields["timestamp_unix"] = (fields["timestamp"] - datetime(1970,1,1, tzinfo=fields["timestamp"].tzinfo)) / timedelta(seconds=1)
        fields["year"] = fields["timestamp"].strftime("%Y")
        fields["month"] = fields["timestamp"].strftime("%m")
        fields["day"] = fields["timestamp"].strftime("%d")
        fields["hour"] = fields["timestamp"].strftime("%-H")
        fields["country"] = None
        fields["city"] = None
        fields["region"] = None
        fields["postal_code"] = None
        fields["latitude"] = None
        fields["longitude"] = None

        if "referrer" in fields:
            fields["referrer_domain"] = urlparse(fields["referrer"]).netloc or None
        else:
            fields["referrer_domain"] = None

        for key, value in fields["extras"].items():
            if value in ("ZZ", "?"):
                value = None
            elif key == "country":
                value = value.upper()
            elif key == "city":
                value = value.title()
            elif key == "region" and len(value) == 2:
                value = value.upper()
            elif key == "latlong" and "," in value:
                fields["latitude"], fields["longitude"] = value.split(",")

            fields[key] = value

        del fields["extras"]
        return fields

    def parseLogQuery(self, val):
        """Convert a logindex query to sql

        The query is used to build the WHERE clause of an SQL query, which is otherwise
        built within the logindex plugin. The parsing that occurs here deals with things like
        exact and wildcard matching, multiple values for the same field, and basic boolean logic.

        The query is expected to be a multi-line string containing
        space-separated field names and search values.
        """

        val = val.replace("\r", "").strip().replace("\n", "|")
        result = self.logquery_grammar.parseString(val).asList()

        sql = " AND ".join(result)
        return sql
