"""Date and time calculations."""

import calendar
from datetime import datetime, timedelta
import typing
import cherrypy
from pytz import timezone, UTC

DatetimeOrString = typing.Union[datetime, str]
OptionalDatetime = typing.Optional[datetime]
IntOrFloat = typing.Union[int, float]


class Plugin(cherrypy.process.plugins.SimplePlugin):
    """A CherryPy plugin for date and time calculations."""

    ymd = "%Y-%m-%d"

    def __init__(self, bus: cherrypy.process.wspbus.Bus) -> None:
        cherrypy.process.plugins.SimplePlugin.__init__(self, bus)

    def start(self) -> None:
        """Define the CherryPy messages to listen for.

        This plugin owns the clock prefix.
        """

        self.bus.subscribe("clock:same_day", self.same_day)
        self.bus.subscribe("clock:now", self.now)
        self.bus.subscribe("clock:format", self.format)
        self.bus.subscribe("clock:from_timestamp", self.from_timestamp)
        self.bus.subscribe("clock:from_format", self.from_format)
        self.bus.subscribe("clock:month:start", self.month_start)
        self.bus.subscribe("clock:month:end", self.month_end)
        self.bus.subscribe("clock:month:next", self.month_next)
        self.bus.subscribe("clock:month:previous", self.month_previous)
        self.bus.subscribe("clock:shift", self.shift)
        self.bus.subscribe("clock:day:remaining", self.day_remaining)

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

    @staticmethod
    def from_timestamp(timestamp: IntOrFloat) -> datetime:
        """Convert a Unix timestamp to a datetime."""

        return datetime.fromtimestamp(timestamp, UTC)

    @staticmethod
    def from_format(value: str, fmt: str) -> OptionalDatetime:
        """Parse a date string in a known format."""

        try:
            dt = datetime.strptime(value, fmt).astimezone(UTC)
        except ValueError:
            return None

        return dt

    @staticmethod
    def month_start(dt: datetime) -> datetime:
        """Rewind a date to the first day of the month."""

        return dt.replace(day=1)

    @staticmethod
    def month_end(dt: datetime) -> datetime:
        """Fast-forward a date to the last day of the month."""

        cal = calendar.monthrange(dt.year, dt.month)

        return dt.replace(day=cal[1])

    @staticmethod
    def month_previous(dt: datetime) -> datetime:
        """Roll back a date to the first day of the previous month."""

        start_date = dt.replace(day=1)

        if start_date.month == 1:
            previous_month = start_date.replace(
                month=12,
                year=(start_date.year - 1)
            )
        else:
            previous_month = start_date.replace(
                month=(start_date.month - 1)
            )

        return previous_month

    @staticmethod
    def month_next(dt: datetime) -> datetime:
        """Advance a date to the first day of the next month."""

        start_date = dt.replace(day=1)

        if start_date.month == 12:
            next_month = start_date.replace(
                month=1,
                year=(start_date.year + 1),
            )
        else:
            next_month = start_date.replace(
                month=(start_date.month + 1)
            )

        return next_month

    @staticmethod
    def now() -> datetime:
        """The current date and time in UTC."""

        return datetime.now(timezone("UTC"))

    @staticmethod
    def shift(dt: datetime, **kwargs: typing.Union[float, str]) -> datetime:
        """Roll forwards or backwards in time."""

        result = dt

        if "timezone" in kwargs:
            tz = timezone(typing.cast(str, kwargs["timezone"]))
            result = result.astimezone(tz)

        if "days" in kwargs:
            days = typing.cast(float, kwargs["days"])
            result = result + timedelta(days=days)

        if "hours" in kwargs:
            hours = typing.cast(float, kwargs["hours"])
            result = result + timedelta(hours=hours)

        return result
