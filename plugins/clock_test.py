"""Test suite for the clock plugin."""

from datetime import datetime
import typing
import unittest
from unittest.mock import Mock, patch, DEFAULT
import cherrypy
import pytz
import plugins.clock
from testing.assertions import Subscriber


class TestClock(Subscriber):
    """Tests for the clock plugin."""

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

        def side_effect(*args: str, **_kwargs: str) -> typing.Any:
            """Side effects local function"""
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
        self.assertTrue(self.plugin.same_day(dt, None))

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
        result = typing.cast(
            datetime,
            self.plugin.shift(start, days=1)
        )
        self.assertEqual(result.day, 5)

        result = typing.cast(
            datetime,
            self.plugin.shift(start, "month_start")
        )
        self.assertEqual(result.day, 1)

        result = typing.cast(
            datetime,
            self.plugin.shift(start, "month_end")
        )
        self.assertEqual(result.day, 31)

        result = typing.cast(
            datetime,
            self.plugin.shift(start, "month_previous")
        )
        self.assertEqual(result.month, 12)
        self.assertEqual(result.year, 2009)

        result = typing.cast(
            datetime,
            self.plugin.shift(start, "month_next")
        )
        self.assertEqual(result.month, 2)
        self.assertEqual(result.year, 2010)

        result = typing.cast(
            datetime,
            self.plugin.shift(start, days=-1)
        )
        self.assertEqual(result.day, 3)

        result = typing.cast(
            datetime,
            self.plugin.shift(start, hours=1)
        )
        self.assertEqual(result.hour, 1)

        result = typing.cast(
            datetime,
            self.plugin.shift(start, hours=-1)
        )
        self.assertEqual(result.hour, 23)

        result = typing.cast(
            datetime,
            self.plugin.shift(start, minutes=1)
        )
        self.assertEqual(result.minute, 1)

    @patch("cherrypy.engine.publish")
    def test_local_with_config(self, publish_mock: Mock) -> None:
        """clock:local performs timezone conversion using a configured zone."""

        def side_effect(*args: str, **_: str) -> typing.Any:
            """Side effects local function"""
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

        def side_effect(*args: str, **_: str) -> typing.Any:
            """Side effects local function"""
            if args[0] == "registry:first:value":
                return [None]
            return DEFAULT

        publish_mock.side_effect = side_effect

        tz = pytz.timezone("UTC")
        start = datetime(2011, 1, 1, hour=00, tzinfo=tz)
        result = self.plugin.local(start)

        now = datetime.now().astimezone()

        self.assertEqual(
            result.strftime("%Z"),
            now.strftime("%Z")
        )
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


if __name__ == "__main__":
    unittest.main()
