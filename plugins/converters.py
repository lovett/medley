"""Custom datatype conversions for use with Python's DB-API interface."""

import datetime
import pickle
import re
import urllib
import sqlite3
from tzlocal import get_localzone
import cherrypy
import msgpack
import pytz
import pendulum


class Plugin(cherrypy.process.plugins.SimplePlugin):
    """A CherryPy plugin that registers sqlite3 datatype converters.

    Unlike other plugins, this one doesn't subscribe to any events and
    isn't meant for pubsub interaction.

    """

    def __init__(self, bus):
        cherrypy.process.plugins.SimplePlugin.__init__(self, bus)

    def start(self):
        """Register converters."""
        sqlite3.register_converter("datetime", self.datetime)
        sqlite3.register_converter("binary", self.binary)
        sqlite3.register_converter("calldate_to_utc", self.calldate_to_utc)
        sqlite3.register_converter("duration", self.duration)
        sqlite3.register_converter("clid", self.callerid)
        sqlite3.register_converter("querystring", self.querystring)

    @staticmethod
    def datetime(value):
        """Convert a datetime string to a datetime instance."""

        value = value.decode("utf-8")
        try:
            date = datetime.datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
            return pytz.utc.localize(date)
        except ValueError:
            last_colon_index = value.rindex(":")
            date = value[:last_colon_index] + value[last_colon_index + 1:]
            return datetime.datetime.strptime(date, "%Y-%m-%d %H:%M:%S%z")

    @staticmethod
    def local_timezone():
        """Determine the timezone of the application.

        The registry is checked first so that the application timezone
        can be independent of the server's timezone. But the server's
        timezone also acts as a fallback.

        """

        timezone = cherrypy.engine.publish(
            "registry:first_value",
            "config:timezone",
            memorize=True
        ).pop()

        if not timezone:
            timezone = pendulum.now().timezone.name

        return timezone

    def calldate_to_utc(self, value):
        """Convert a local datetime string to a UTC Pendulum instance."""

        local_tz = self.local_timezone()

        return pendulum.from_format(
            value.decode("utf-8"),
            "YYYY-MM-DD HH:mm:ss",
            tz=local_tz,
        ).in_timezone('utc')

    @staticmethod
    def duration(value):
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
            result.append("{} {}".format(hours, hours_label))

        if minutes > 0:
            result.append("{} {}".format(minutes, minutes_label))

        if seconds > 0:
            result.append("{} {}".format(seconds, seconds_label))

        if not result:
            result.append("0 {}".format(seconds_label))

        return ", ".join(result)

    @staticmethod
    def callerid(value):
        """De-quote a caller ID string from an Asterisk CDR database."""

        return re.sub(r'"(.*?)".*', r"\1", value.decode("utf-8"))

    @staticmethod
    def binary(blob):
        """Unpack a binary value stored in a blob field.

        MessagePack is the only serialization format used by the
        application, but fall back to pickle since that was the format
        used before MessagePack was implemented.

        """

        try:
            return msgpack.unpackb(blob, encoding='utf-8')
        except msgpack.exceptions.ExtraData:
            return pickle.loads(blob)

    @staticmethod
    def querystring(value):
        """Parse a URL querystring into a dict."""

        return urllib.parse.parse_qs(
            value.decode("utf-8"),
            keep_blank_values=True
        )
