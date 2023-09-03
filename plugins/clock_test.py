"""Test suite for the clock plugin."""

from collections import namedtuple
from datetime import datetime
import time
from typing import Any
from typing import cast
import unittest
from unittest.mock import Mock, patch, DEFAULT
import cherrypy
import pytz
import plugins.clock
from testing.assertions import Subscriber


class TestClock(Subscriber):

    def setUp(self) -> None:
        self.plugin = plugins.clock.Plugin(cherrypy.engine)

    @patch("cherrypy.engine.subscribe")
    def test_subscribe(self, subscribe_mock: Mock) -> None:
        """Subscriptions are prefixed consistently."""

        self.plugin.start()
        self.assert_prefix(subscribe_mock, "clock")

    def test_now(self) -> None:
        """clock:now returns a datetime in UTC."""

        self.assertEqual(
            self.plugin.now().tzinfo,
            pytz.UTC
        )

    @patch("cherrypy.engine.publish")
    def test_now_local(self, publish_mock: Mock) -> None:
        """clock:now can return a local time."""

        def side_effect(*args: str, **_kwargs: str) -> Any:
            if args[0] == "registry:first:value":
                return ["America/New_York"]
            return DEFAULT

        publish_mock.side_effect = side_effect

        now_local = self.plugin.now(local=True)

        self.assertNotEqual(
            now_local.tzinfo,
            pytz.UTC
        )

    def test_sameday_now(self) -> None:
        """clock:sameday matches dates for the current date."""

        # Reference date is both in the past and not UTC
        ref = datetime(1900, 1, 1, 1, 1, tzinfo=pytz.timezone("US/Pacific"))

        # present vs past
        dt = datetime.now(tz=pytz.UTC)
        self.assertFalse(self.plugin.same_day(dt, ref))

        # two dates in past
        dt = ref.replace(hour=1)
        self.assertTrue(self.plugin.same_day(dt, ref))

        # two dates in present
        dt = datetime.now(tz=pytz.UTC).replace(minute=0)
        self.assertTrue(self.plugin.same_day(dt))

    def test_from_timestamp(self) -> None:
        """clock:from_timestamp handles integer and float timestamps."""

        result = self.plugin.from_timestamp(1)
        self.assertIsInstance(result, datetime)
        self.assertEqual(result.year, 1970)
        self.assertTrue(result.tzinfo, pytz.UTC)

        result = self.plugin.from_timestamp(1.123)
        self.assertIsInstance(result, datetime)
        self.assertEqual(result.month, 1)
        self.assertTrue(result.tzinfo, pytz.UTC)

    def test_from_struct_local(self) -> None:
        """clock:from_struct returns local datetimes for local values."""

        result = self.plugin.from_struct(time.localtime())
        now = datetime.now(pytz.timezone('America/New_York'))

        self.assertIsInstance(result, datetime)
        self.assertEqual(now.year, result.year)
        self.assertEqual(now.month, result.month)
        self.assertEqual(now.day, result.day)
        self.assertEqual(now.hour, result.hour)
        self.assertEqual(now.minute, result.minute)

    def test_from_struct_utc(self) -> None:
        """clock:from_struct returns UTC datetimes for UTC values."""

        result = self.plugin.from_struct(time.gmtime())
        now = datetime.now(pytz.UTC)

        self.assertIsInstance(result, datetime)
        self.assertEqual(now.year, result.year)
        self.assertEqual(now.month, result.month)
        self.assertEqual(now.day, result.day)
        self.assertEqual(now.hour, result.hour)
        self.assertEqual(now.minute, result.minute)

    def test_from_format(self) -> None:
        """clock:from_format handles valid and invalid formats."""

        result = self.plugin.from_format("2020-01-01", self.plugin.ymd)

        if not result:
            self.fail()

        self.assertIsInstance(result, datetime)
        self.assertEqual(result.year, 2020)
        self.assertTrue(result.tzinfo, pytz.UTC)

        result = self.plugin.from_format("garbage input", self.plugin.ymd)

        if result:
            self.fail()

        self.assertIsNone(result)

    def test_day_remaining(self) -> None:
        """clock:day:remaining returns seconds until end-of-day regardless of
        timezone.

        """

        dt = datetime(2000, 1, 1, tzinfo=pytz.timezone("UTC"))
        result = self.plugin.day_remaining(dt)

        self.assertEqual(result, 86399)

        dt = datetime(2000, 1, 1, tzinfo=pytz.timezone("US/Eastern"))
        result = self.plugin.day_remaining(dt)

        self.assertEqual(result, 86399)

    def test_shift(self) -> None:
        """clock:shift moves forward and backward in time."""

        start = datetime(2010, 1, 4, tzinfo=pytz.timezone("UTC"))
        result = cast(
            datetime,
            self.plugin.shift(start, days=1)
        )
        self.assertEqual(result.day, 5)

        result = cast(
            datetime,
            self.plugin.shift(start, "month_start")
        )
        self.assertEqual(result.day, 1)

        result = cast(
            datetime,
            self.plugin.shift(start, "month_end")
        )
        self.assertEqual(result.day, 31)

        result = cast(
            datetime,
            self.plugin.shift(start, "month_previous")
        )
        self.assertEqual(result.month, 12)
        self.assertEqual(result.year, 2009)

        result = cast(
            datetime,
            self.plugin.shift(start, "month_next")
        )
        self.assertEqual(result.month, 2)
        self.assertEqual(result.year, 2010)

        result = cast(
            datetime,
            self.plugin.shift(start, days=-1)
        )
        self.assertEqual(result.day, 3)

        result = cast(
            datetime,
            self.plugin.shift(start, hours=1)
        )
        self.assertEqual(result.hour, 1)

        result = cast(
            datetime,
            self.plugin.shift(start, hours=-1)
        )
        self.assertEqual(result.hour, 23)

        result = cast(
            datetime,
            self.plugin.shift(start, minutes=1)
        )
        self.assertEqual(result.minute, 1)

    @patch("cherrypy.engine.publish")
    def test_local_with_config(self, publish_mock: Mock) -> None:
        """clock:local performs timezone conversion using a configured zone."""

        def side_effect(*args: str, **_: str) -> Any:
            if args[0] == "registry:first:value":
                return ["America/New_York"]
            return DEFAULT

        publish_mock.side_effect = side_effect

        tz = pytz.timezone("UTC")
        start = datetime(2011, 1, 1, hour=00, tzinfo=tz)
        result = self.plugin.local(start)

        self.assertEqual(result.strftime("%Z"), "EST")
        self.assertEqual(result.day, 31)
        self.assertEqual(result.year, 2010)
        self.assertEqual(result.month, 12)

    @patch("cherrypy.engine.publish")
    def test_local_without_config(self, publish_mock: Mock) -> None:
        """clock:local performs timezone conversion using the system zone."""

        def side_effect(*args: str, **_: str) -> Any:
            if args[0] == "registry:first:value":
                return [None]
            return DEFAULT

        publish_mock.side_effect = side_effect

        tz = pytz.timezone("UTC")
        start = datetime(2011, 1, 1, hour=00, tzinfo=tz)
        result = self.plugin.local(start)

        self.assertEqual(result.day, 31)
        self.assertEqual(result.year, 2010)
        self.assertEqual(result.month, 12)

    def test_duration_words(self) -> None:
        """clock:duration:words converts timespans to strings."""

        result = self.plugin.duration_words(days=1, hours=1, minutes=1)
        self.assertEqual(result, "1 day")

        result = self.plugin.duration_words(hours=1)
        self.assertEqual(result, "1 hour")

        result = self.plugin.duration_words(hours=2)
        self.assertEqual(result, "2 hours")

        result = self.plugin.duration_words(minutes=61)
        self.assertEqual(result, "1 hour")

        result = self.plugin.duration_words(minutes=62)
        self.assertEqual(result, "1 hour")

        result = self.plugin.duration_words(seconds=1)
        self.assertEqual(result, "1 second")

        result = self.plugin.duration_words(seconds=2)
        self.assertEqual(result, "2 seconds")

        result = self.plugin.duration_words(seconds=0)
        self.assertEqual(result, "")

    def test_scheduled_success(self) -> None:
        """A schedule is active when a datetime is in-range."""

        now = datetime.now()

        Case = namedtuple(
            "Case",
            ["schedule", "hour", "minute", "result", "label"])

        cases = (
            Case("11:00 PM\n9:00 AM", 23, 0, True, "start"),
            Case("11:00 PM\n9:00 AM", 22, 59, False, "before start"),
            Case("11:00 PM\n9:00 AM", 23, 1, True, "after start"),
            Case("11:00 PM\n9:00 AM", 9, 0, True, "end"),
            Case("11:00 PM\n9:00 AM", 8, 59, True, "before end"),
            Case("11:00 PM\n9:00 AM", 10, 0, False, "after end"),
            Case("11:00 PM\n9:00 AM", 0, 0, True, "midnight"),
            Case("11:00 AM\n12:00 PM", 11, 0, True, "start 2"),
            Case("11:00 AM\n12:00 PM", 10, 59, False, "before start 2"),
            Case("11:00 AM\n12:00 PM", 11, 1, True, "after start 2"),
            Case("11:00 AM\n12:00 PM", 12, 0, True, "end 2"),
            Case("11:00 AM\n12:00 PM", 11, 59, True, "before end 2"),
            Case("11:00 AM\n12:00 PM", 12, 1, False, "after end 2"),
        )

        for case in cases:
            result = self.plugin.scheduled(
                [case.schedule],
                now.replace(
                    hour=case.hour,
                    minute=case.minute,
                    second=0,
                    microsecond=0
                )
            )
            self.assertEqual(result, case.result, case.label)


if __name__ == "__main__":
    unittest.main()
