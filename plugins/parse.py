"""Grammar-based parsing using pyparsing."""

import string
import typing
from urllib.parse import urlparse
import pyparsing as pp
import cherrypy
import pendulum


class Plugin(cherrypy.process.plugins.SimplePlugin):
    """A CherryPy plugin for interacting with pyparsing grammars."""

    def __init__(self, bus: cherrypy.process.wspbus.Bus) -> None:
        cherrypy.process.plugins.SimplePlugin.__init__(self, bus)

    def start(self) -> None:
        """Define the CherryPy messages to listen for.

        This plugin owns the parse prefix.
        """

        self.bus.subscribe("parse:grammar:appengine", self.appengine_grammar)
        self.bus.subscribe("parse:appengine", self.parse_appengine)

    def appengine_grammar(self) -> pp.And:
        """Generate the grammar used to parse Appengine logs.

        Field order is documented at:
        https://cloud.google.com/appengine/docs/python/logs/
        """
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

        return appengine_fields

    @staticmethod
    def request_fields(
            _string: str,
            _location: int,
            tokens: pp.ParseResults
    ) -> None:
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
    def first_in_group(
            _string: str,
            _location: int,
            tokens: pp.ParseResults
    ) -> str:
        """Return the first item in a group."""
        return typing.cast(str, tokens[0][0])

    @staticmethod
    def dash_to_none(
            _string: str,
            _location: int,
            tokens: pp.ParseResults
    ) -> typing.Optional[str]:
        """Coerce a bare hypen to None"""
        if tokens[0] == "-":
            return None

        return typing.cast(str, tokens[0])

    @staticmethod
    def to_dict(
            _string: str,
            _location: int,
            tokens: pp.ParseResults
    ) -> typing.Dict[str, typing.Any]:
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

    @staticmethod
    def parse_appengine(
            grammar: typing.Any,
            val: str
    ) -> typing.Dict[str, typing.Any]:
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
            fields = typing.cast(
                typing.Dict[str, typing.Any],
                grammar.parseString(val).asDict()
            )
        except pp.ParseException as exception:
            cherrypy.engine.publish(
                "applog:add",
                "parse:exception",
                f"Column {exception.col} of {val}"
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
