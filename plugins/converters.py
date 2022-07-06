"""Custom datatype conversions for use with Python's DB-API interface."""

from datetime import datetime
import json
import re
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import cast
import urllib.parse
from sqlite3 import register_converter  # pylint: disable=no-name-in-module
import cherrypy
from resources.url import Url


class Plugin(cherrypy.process.plugins.SimplePlugin):
    """A CherryPy plugin that registers sqlite3 datatype converters.

    Unlike other plugins, this one doesn't subscribe to any events and
    isn't meant for pubsub interaction.

    """

    def __init__(self, bus: cherrypy.process.wspbus.Bus) -> None:
        cherrypy.process.plugins.SimplePlugin.__init__(self, bus)

    def start(self) -> None:
        """Register converters."""
        register_converter("local_datetime", self.local_datetime)
        register_converter("utc", self.utc)
        register_converter("date_with_hour", self.date_with_hour)
        register_converter("json", self.json)
        register_converter("duration", self.duration)
        register_converter("clid", self.callerid)
        register_converter("querystring", self.querystring)
        register_converter("comma_delimited", self.comma_delimited)
        register_converter("slug", self.slug)
        register_converter("url", self.url)

    @staticmethod
    def local_datetime(value: bytes) -> datetime:
        """Convert a string to a datetime in the application timezone."""

        decoded_value = value.decode("utf-8")

        dt = cherrypy.engine.publish(
            "clock:from_format",
            decoded_value,
            "%Y-%m-%d %H:%M:%S"
        ).pop()

        if not dt:
            dt = cherrypy.engine.publish(
                "clock:from_format",
                decoded_value,
                "%Y-%m-%d %H:%M:%S%z"
            ).pop()

        if not dt:
            dt = cherrypy.engine.publish(
                "clock:from_format",
                decoded_value,
                "%Y-%m-%d %H:%M:%S.%f%z"
            ).pop()

        return cast(
            datetime,
            cherrypy.engine.publish(
                "clock:local",
                dt
            ).pop()
        )

    @staticmethod
    def utc(value: bytes) -> datetime:
        """Convert a naieve string to a UTC datetime."""

        return cast(
            datetime,
            cherrypy.engine.publish(
                "clock:from_format",
                value.decode("utf-8"),
                "%Y-%m-%d %H:%M:%S.%f"
            ).pop()
        )

    @staticmethod
    def date_with_hour(value: bytes) -> Optional[datetime]:
        """Convert a date-and-hour string to a Pendulum instance."""

        decoded_value = value.decode("utf-8")
        dt = cherrypy.engine.publish(
            "clock:from_format",
            decoded_value,
            "%Y-%m-%d-%H"
        ).pop()

        if not dt:
            return None

        return cast(datetime, dt)

    @staticmethod
    def duration(value: bytes) -> str:
        """Convert a number of seconds into a human-readable string."""

        seconds = int(value)

        if seconds == 1:
            return f"{seconds} second"

        if 60 < seconds <= 90:
            return f"{seconds} seconds"

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
    def querystring(value: bytes) -> Dict[str, List[str]]:
        """Parse a URL querystring into a dict."""

        return urllib.parse.parse_qs(
            value.decode("utf-8"),
            keep_blank_values=True
        )

    @staticmethod
    def comma_delimited(value: bytes) -> List[str]:
        """Parse a comma-delimited string into a list."""

        return [
            word.strip()
            for word in value.decode("utf-8").split(",")
        ]

    @staticmethod
    def json(value: bytes) -> Any:
        """Parse a value stored as JSON."""

        return json.loads(value.decode("utf-8"))

    @staticmethod
    def slug(value: bytes) -> str:
        """Generate the slug of a string."""

        return re.sub(r" ", "-", value.decode("utf-8")).lower()

    @staticmethod
    def url(value: bytes) -> Url:
        """Convert a URL string to a URL resource."""

        return Url(value.decode("utf-8") or "")
