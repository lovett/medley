"""Custom datatype conversions for use with Python's DB-API interface."""

import re
import typing
import urllib
from sqlite3 import register_converter  # pylint: disable=no-name-in-module
import cherrypy
import msgpack
import pendulum


class Plugin(cherrypy.process.plugins.SimplePlugin):
    """A CherryPy plugin that registers sqlite3 datatype converters.

    Unlike other plugins, this one doesn't subscribe to any events and
    isn't meant for pubsub interaction.

    """

    def __init__(self, bus: cherrypy.process.wspbus.Bus) -> None:
        cherrypy.process.plugins.SimplePlugin.__init__(self, bus)

    def start(self) -> None:
        """Register converters."""
        register_converter("datetime", self.datetime)
        register_converter("date_with_hour", self.date_with_hour)
        register_converter("binary", self.binary)
        register_converter("calldate_to_utc", self.calldate_to_utc)
        register_converter("duration", self.duration)
        register_converter("clid", self.callerid)
        register_converter("querystring", self.querystring)
        register_converter("comma_delimited", self.comma_delimited)

    @staticmethod
    def datetime(value: bytes) -> pendulum.DateTime:
        """Convert a datetime string to a Pendulum instance."""

        decoded_value = value.decode("utf-8")

        try:
            utc_date = pendulum.from_format(
                decoded_value,
                "YYYY-MM-DD HH:mm:ss"
            )
        except ValueError:
            last_colon_index = decoded_value.rindex(":")
            date = decoded_value[:last_colon_index] + \
                decoded_value[last_colon_index + 1:]
            utc_date = pendulum.from_format(date, "YYYY-MM-DD HH:mm:ssZZ")

        return utc_date

    @staticmethod
    def date_with_hour(value: bytes) -> typing.Optional[pendulum.DateTime]:
        """Convert a date-and-hour string to a Pendulum instance."""

        decoded_value = value.decode("utf-8")

        try:
            utc_date = pendulum.from_format(decoded_value, "YYYY-MM-DD-HH")
        except ValueError:
            utc_date = None

        return utc_date

    @staticmethod
    def calldate_to_utc(value: bytes) -> pendulum.DateTime:
        """Convert a local datetime string to a UTC Pendulum instance."""

        local_tz = cherrypy.engine.publish(
            "registry:timezone"
        ).pop()

        return pendulum.from_format(
            value.decode("utf-8"),
            "YYYY-MM-DD HH:mm:ss",
            tz=local_tz,
        ).in_timezone('utc')

    @staticmethod
    def duration(value: bytes) -> str:
        """Convert a number of seconds into a human-readable string."""

        seconds = int(value)
        hours_label = "hour"
        minutes_label = "minute"
        seconds_label = "second"

        hours = seconds // 3600
        seconds -= hours * 3600
        if hours != 1:
            hours_label += "s"

        minutes = seconds // 60
        seconds -= minutes * 60

        if minutes != 1:
            minutes_label += "s"

        if seconds != 1:
            seconds_label += "s"

        result = []
        if hours > 0:
            result.append(f"{hours} {hours_label}")

        if minutes > 0:
            result.append(f"{minutes} {minutes_label}")

        if seconds > 0:
            result.append(f"{seconds} {seconds_label}")

        if not result:
            result.append(f"0 {seconds_label}")

        return ", ".join(result)

    @staticmethod
    def callerid(value: bytes) -> str:
        """De-quote a caller ID string from an Asterisk CDR database."""

        return re.sub(r'"(.*?)".*', r"\1", value.decode("utf-8"))

    @staticmethod
    def binary(blob: bytes) -> typing.Any:
        """Unpack a binary value stored in a blob field.

        MessagePack is the only serialization format used by the
        application.

        """

        try:
            return msgpack.unpackb(blob, encoding='utf-8')
        except msgpack.exceptions.ExtraData:
            return None

    @staticmethod
    def querystring(value: bytes) -> typing.Dict[str, typing.List[str]]:
        """Parse a URL querystring into a dict."""

        return urllib.parse.parse_qs(
            value.decode("utf-8"),
            keep_blank_values=True
        )

    @staticmethod
    def comma_delimited(value: bytes) -> typing.List[str]:
        """Parse a comma-delimited string into a list."""

        return [
            word.strip()
            for word in value.decode("utf-8").split(',')
        ]
