"""Date and time calculations."""

import calendar
from datetime import datetime, timedelta, date
from time import struct_time
from typing import Optional
from typing import List
from typing import Union
from typing import cast
import cherrypy
from pytz import timezone, UTC, UnknownTimeZoneError

DatetimeOrString = Union[datetime, str]
OptionalDatetime = Optional[datetime]


class Plugin(cherrypy.process.plugins.SimplePlugin):
    """A CherryPy plugin for date and time calculations."""

    ymd = "%Y-%m-%d"

    def __init__(self, bus: cherrypy.process.wspbus.Bus) -> None:
        cherrypy.process.plugins.SimplePlugin.__init__(self, bus)

    def start(self) -> None:
        """Define the CherryPy messages to listen for.

        This plugin owns the clock prefix.
        """

        self.bus.subscribe("clock:ago", self.ago)
        self.bus.subscribe("clock:duration:words", self.duration_words)
        self.bus.subscribe("clock:same_day", self.same_day)
        self.bus.subscribe("clock:now", self.now)
        self.bus.subscribe("clock:now_unix", self.now_unix)
        self.bus.subscribe("clock:format", self.format)
        self.bus.subscribe("clock:from_timestamp", self.from_timestamp)
        self.bus.subscribe("clock:from_format", self.from_format)
        self.bus.subscribe("clock:from_struct", self.from_struct)
        self.bus.subscribe("clock:shift", self.shift)
        self.bus.subscribe("clock:local", self.local)
        self.bus.subscribe("clock:day:remaining", self.day_remaining)
        self.bus.subscribe("clock:utc", self.utc)
        self.bus.subscribe("clock:scheduled", self.scheduled)

    def day_remaining(self, dt: datetime = None) -> int:
        """Calculate how many seconds are left in the day."""

        dt = dt or self.now()
        dt = dt.replace(tzinfo=None)
        end = dt.replace(hour=23, minute=59, second=59)

        return (end - dt).seconds

    def same_day(self, dt1: datetime, dt2: datetime = None) -> bool:
        """Determine whether two dates fall on the same day."""

        dt1 = dt1.replace(tzinfo=None)

        dt2 = dt2 or self.now()
        dt2.replace(tzinfo=None)

        return self.format(dt1, self.ymd) == self.format(dt2, self.ymd)

    @staticmethod
    def format(dt: datetime, fmt: str) -> str:
        """Convert a datetime to a string in the given format."""

        return dt.strftime(fmt)

    def from_timestamp(
            self,
            timestamp: float,
            local: bool = False
    ) -> datetime:
        """Convert a Unix timestamp to a datetime."""

        dt = datetime.fromtimestamp(timestamp, UTC)

        if local:
            return self.local(dt)

        return dt

    def from_format(
            self,
            value: str,
            fmt: str,
            local: bool = False
    ) -> OptionalDatetime:
        """Parse a date string in a known format."""

        try:
            dt = datetime.strptime(value, fmt).replace(tzinfo=UTC)
            if local:
                return self.local(dt)
            return dt
        except ValueError:
            return None

    @staticmethod
    def from_struct(
            time_struct: struct_time,
    ) -> datetime:
        """Parse a time tuple into a datetime."""
        return datetime(*time_struct[:6])

    def now(self, local: bool = False) -> datetime:
        """The current date and time in UTC."""

        if local:
            return self.local(datetime.now(UTC))
        return datetime.now(UTC)

    @staticmethod
    def now_unix() -> float:
        """The current date and time as a Unix timestamp."""
        return datetime.now(UTC).timestamp()

    @staticmethod
    def shift(
            dt: Union[date, datetime],
            *args: str,
            **kwargs: Union[float, str]
    ) -> Union[date, datetime]:
        """Roll forwards or backwards in time."""

        result = dt

        if "month_start" in args:
            result = result.replace(day=1)

        if "month_end" in args:
            cal = calendar.monthrange(result.year, result.month)
            result = result.replace(day=cal[1])

        if "month_previous" in args:
            month = result.month - 1
            year = result.year
            if result.month == 1:
                month = 12
                year -= 1
            result = result.replace(month=month, year=year)

        if "month_next" in args:
            month = result.month + 1
            year = result.year
            if result.month == 12:
                month = 1
                year += 1
            result = result.replace(month=month, year=year)

        if "days" in kwargs:
            days = cast(float, kwargs["days"])
            result = result + timedelta(days=days)

        if "hours" in kwargs:
            hours = cast(float, kwargs["hours"])
            result = result + timedelta(hours=hours)

        if "minutes" in kwargs:
            minutes = cast(float, kwargs["minutes"])
            result = result + timedelta(minutes=minutes)

        return result

    @staticmethod
    def utc(dt: datetime) -> datetime:
        """Convert a datetime to UTC."""

        return dt.astimezone(UTC)

    @staticmethod
    def local(dt: datetime) -> datetime:
        """Convert a datetime to the local timezone."""

        local_timezone = cherrypy.engine.publish(
            "registry:first:value",
            "config:timezone",
            memorize=True
        ).pop()

        try:
            dt = dt.astimezone(
                timezone(local_timezone)
            )
        except UnknownTimeZoneError:
            dt = dt.astimezone(
                datetime.now().astimezone().tzinfo
            )

        return dt

    def ago(self, value: datetime) -> str:
        """Describe a timedelta in words."""

        delta = self.now(local=True) - value

        return self.duration_words(
            seconds=int(delta.total_seconds())
        )

    @staticmethod
    def duration_words(**kwargs: int) -> str:
        """Describe a numeric timespan in words."""

        total_seconds = 0

        if "days" in kwargs:
            total_seconds += kwargs["days"] * 86400

        if "hours" in kwargs:
            total_seconds += kwargs["hours"] * 3600

        if "minutes" in kwargs:
            total_seconds += kwargs["minutes"] * 60

        if "seconds" in kwargs:
            total_seconds += kwargs["seconds"]

        if total_seconds >= 604800:
            count, total_seconds = divmod(total_seconds, 604800)
            label = "weeks"
            if count == 1:
                label = "week"

            return f"{count} {label}"

        if total_seconds >= 86400:
            count, total_seconds = divmod(total_seconds, 86400)
            label = "days"
            if count == 1:
                label = "day"
            return f"{count} {label}"

        if total_seconds >= 3600:
            count, total_seconds = divmod(total_seconds, 3600)
            label = "hours"
            if count == 1:
                label = "hour"
            return f"{count} {label}"

        if total_seconds >= 60:
            count, total_seconds = divmod(total_seconds, 60)
            label = "minutes"
            if count == 1:
                label = "minute"
            return f"{count} {label}"

        if total_seconds > 0:
            label = "seconds"
            if total_seconds == 1:
                label = "second"
            return f"{total_seconds} {label}"

        return ""

    @staticmethod
    def scheduled(schedules: List[str]) -> bool:
        """Whether the current time falls within a set of ranges."""

        today = date.today()
        tomorrow = today + timedelta(1)
        now = datetime.now()

        for schedule in schedules:
            schedule_lines = [
                line.rstrip()
                for line in schedule.split("\n")
            ]

            for time_format in ("%I:%M %p", "%H:%M"):
                try:
                    time_range = [
                        datetime.strptime(line, time_format)
                        for line in schedule_lines
                    ]
                    break
                except ValueError:
                    return False

            start = datetime.combine(today, time_range[0].time())

            if time_range[1] < time_range[0]:
                end = datetime.combine(tomorrow, time_range[1].time())
            else:
                end = datetime.combine(today, time_range[1].time())

            if start <= now <= end:
                return True

        return False
