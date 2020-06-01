"""Test suite for the clock plugin."""

from datetime import datetime
import unittest
from unittest.mock import Mock, patch
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

    def test_month_start(self) -> None:
        """clock:month:start identifies the first day of the month."""

        tz = pytz.timezone("US/Mountain")
        dt = datetime(1999, 2, 2, 2, 2, tzinfo=tz)

        result = self.plugin.month_start(dt)

        self.assertEqual(result.day, 1)
        self.assertEqual(result.tzinfo, tz)

    def test_month_end(self) -> None:
        """clock:month:end identifies the last day of the month."""

        tz = pytz.timezone("US/Eastern")
        dt = datetime(1995, 2, 2, 2, 2, tzinfo=tz)
        result = self.plugin.month_end(dt)

        self.assertEqual(result.day, 28)

        dt = datetime(1996, 2, 2, 2, 2, tzinfo=tz)
        result = self.plugin.month_end(dt)

        self.assertEqual(result.day, 29)
        self.assertEqual(result.tzinfo, tz)

    def test_month_next(self) -> None:
        """clock:month:next handles year boundary."""

        dt = datetime(1955, 12, 12, 12, 12)
        result = self.plugin.month_next(dt)

        self.assertEqual(result.month, 1)
        self.assertEqual(result.year, 1956)

        dt = datetime(1954, 11, 11, 11, 11)
        result = self.plugin.month_next(dt)

        self.assertEqual(result.month, 12)
        self.assertEqual(result.year, 1954)

    def test_month_previous(self) -> None:
        """clock:month:previous handles year boundary."""

        dt = datetime(1940, 1, 1, 1, 1)
        result = self.plugin.month_previous(dt)

        self.assertEqual(result.month, 12)
        self.assertEqual(result.year, 1939)

        dt = datetime(1920, 11, 11, 11, 11)
        result = self.plugin.month_previous(dt)

        self.assertEqual(result.month, 10)
        self.assertEqual(result.year, 1920)

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

        start = datetime(2010, 4, 4, tzinfo=pytz.timezone("UTC"))
        result = self.plugin.shift(start, days=1)
        self.assertEqual(result.day, 5)

        result = self.plugin.shift(start, days=-1)
        self.assertEqual(result.day, 3)

        result = self.plugin.shift(start, hours=1)
        self.assertEqual(result.hour, 1)

        result = self.plugin.shift(start, hours=-1)
        self.assertEqual(result.hour, 23)

    def test_shift_timezone(self) -> None:
        """clock:shift can perform timezone conversion."""

        tz = pytz.timezone("US/Eastern")
        start = datetime(2011, 5, 5, hour=23, tzinfo=tz)
        result = self.plugin.shift(start, timezone="UTC")

        self.assertEqual(result.tzinfo, pytz.UTC)
        self.assertEqual(result.day, 6)


if __name__ == "__main__":
    unittest.main()
