"""Parser for logs in combined format."""

import typing
from urllib.parse import urlparse
import pendulum

OptionalString = typing.Optional[str]
ConsumeResult = typing.Tuple[OptionalString, str]
ExtrasDict = typing.Dict[str, OptionalString]
FieldsDict = typing.Dict[
    str,
    typing.Union[OptionalString, int, ExtrasDict]
]


class Parser():
    """Break up a log line into its component fields."""

    @staticmethod
    def clean(bag: str) -> typing.Optional[str]:
        """Sanitize a value to a normalized form."""

        if isinstance(bag, str):
            bag = bag.strip('" ')

            if len(bag) == 0 or bag == "-":
                return None

        return bag

    @staticmethod
    def parse_timestamp(timestamp: str) -> typing.Optional[pendulum.DateTime]:
        """Parse a timestamp based on known formats."""

        timestamp = timestamp.lstrip("[").rstrip("]")

        format_strings = (
            "DD/MMM/YYYY:HH:mm:ss ZZ",
            "DD/MMM/YYYY:HH:mm:ss:SSSSSS ZZ"
        )

        for format_string in format_strings:
            try:
                return pendulum.from_format(
                    timestamp,
                    format_string
                ).in_tz("utc")
            except ValueError:
                pass

        return None

    @staticmethod
    def sanitize_logline(logline: str) -> str:
        """Perform sanity checks and cleanup on a log line."""

        logline = logline.strip()

        # Make sure double-quoted fields are balanced.
        if logline.count('"') % 2 > 0:
            logline = f'{logline}"'

        # Avoid problems with an empty double-quoted
        # string for the referrer field.
        logline = logline.replace(' "" "', ' - "')

        return logline

    def consume(self, bag: str, separator: str) -> ConsumeResult:
        """Partition a string at a separator and return both halves."""

        (before, separator, after) = bag.partition(separator)

        if separator == "" and after == "":
            return ("", before)

        return (
            self.clean(f"{before}{separator}"),
            after.lstrip()
        )

    def parse(self, logline: str) -> typing.Any:
        """Convert a log line to a dict.

        On top of the standard fields of the combined log format, this
        also supports key-and-quoted-value pairs tacked on at the
        end. This is how AppEngine captures geoip information.

        Field order is documented at:
        https://cloud.google.com/appengine/docs/python/logs/

        """

        logline = self.sanitize_logline(logline)

        fields: FieldsDict = {
            "extras": {}
        }

        # Client Address
        fields["ip"], logline = self.consume(logline, " ")

        # Identity
        fields["identity"], logline = self.consume(logline, " ")

        # User
        fields["user"], logline = self.consume(logline, " ")

        # Timestamp
        fields["timestamp"], logline = self.consume(logline, "]")
        if isinstance(fields["timestamp"], str):
            parsed_timestamp = self.parse_timestamp(fields["timestamp"])
            if parsed_timestamp:
                fields["unix_timestamp"] = parsed_timestamp.timestamp()
                fields["datestamp"] = parsed_timestamp.format("YYYY-MM-DD-HH")

        # Method
        fields["method"], logline = self.consume(logline, " ")

        # Path
        fields["uri"], logline = self.consume(logline, " ")

        # Querystring
        if isinstance(fields["uri"], str) and "?" in fields["uri"]:
            (uri, _, query) = typing.cast(str, fields["uri"]).partition("?")
            fields["uri"] = uri
            fields["query"] = query

        # HTTP Version
        fields["http_version"], logline = self.consume(logline, " ")

        # Status
        fields["statusCode"], logline = self.consume(logline, " ")
        if isinstance(fields["statusCode"], str):
            fields["statusCode"] = int(fields["statusCode"])

        # Response size
        fields["numBytesSent"], logline = self.consume(logline, " ")
        if isinstance(fields["numBytesSent"], str):
            fields["numBytesSent"] = int(fields["numBytesSent"])

        # Referrer
        fields["referrer"], logline = self.consume(logline, " ")
        if isinstance(fields["referrer"], str):
            parsed_referrer = urlparse(fields["referrer"])

            if parsed_referrer.netloc:
                fields["referrer_domain"] = parsed_referrer.netloc

        # User agent
        fields["agent"], logline = self.consume(logline.lstrip('"'), '"')

        # Hostname
        fields["host"], logline = self.consume(logline, " ")

        # Extras
        fields["extras"] = self.parse_extras(logline)

        return fields

    def parse_extras(self, bag: str) -> ExtrasDict:
        """Convert quoted key-value pairs to a dict."""

        extras: ExtrasDict = {}
        key: str = ""
        value: OptionalString = ""

        while "=" in bag:
            key, _, bag = bag.partition('="')
            value, _, bag = bag.partition('" ')

            value = self.clean(value)

            if not value:
                continue

            if value in ("ZZ", "?", ""):
                continue

            if key in ("country", "region"):
                value = value.upper()

            if key == "city":
                value = value.title()

            if key == "latlong" and "," in value:
                extras["latitude"], extras["longitude"] = value.split(",")
                continue

            extras[key] = value

        return extras
