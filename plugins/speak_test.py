"""Test suite for the speak plugin."""

import unittest
from unittest import mock
from typing import Any
import cherrypy
import plugins.speak
from testing.assertions import Subscriber


class TestSpeak(Subscriber):
    """Tests for the speak plugin."""

    def setUp(self) -> None:
        self.plugin = plugins.speak.Plugin(cherrypy.engine)

    def test_muted_temporary(self) -> None:
        """Mute check prioritizes temporary muting."""
        temp_mock = mock.Mock()
        temp_mock.return_value = True
        self.plugin.muted_temporarily = temp_mock  # type: ignore

        schedule_mock = mock.Mock(
            side_effect=Exception('Unwanted call')
        )
        self.plugin.muted_by_schedule = schedule_mock  # type: ignore

        result = self.plugin.muted()
        self.assertTrue(result)

    def test_muted_scheduled(self) -> None:
        """Mute check considers schedules."""
        temp_mock = mock.Mock()
        temp_mock.return_value = False
        self.plugin.muted_temporarily = temp_mock  # type: ignore

        schedule_mock = mock.Mock()
        schedule_mock.return_value = True
        self.plugin.muted_by_schedule = schedule_mock  # type: ignore

        result = self.plugin.muted()
        self.assertTrue(result)

    @mock.patch("cherrypy.engine.publish")
    def test_muted_when_scheduled(self, publish_mock: mock.Mock) -> None:
        """Muted by schedule if a schedule is in range."""

        def side_effect(*args: str, **_: str) -> Any:
            if args[0] == "registry:search:valuelist":
                return ["11:00 PM\n9:00 AM"]
            if args[0] == "clock:scheduled":
                return [True]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        result = self.plugin.muted_by_schedule()

        self.assertTrue(result)

    @mock.patch("cherrypy.engine.publish")
    def test_unmuted_when_no_schedules(self, publish_mock: mock.Mock) -> None:
        """Not muted by schedule if there are no schedules."""

        def side_effect(*args: str, **_: str) -> Any:
            if args[0] == "registry:search:valuelist":
                return [None]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        result = self.plugin.muted_by_schedule()
        self.assertFalse(result)

    @mock.patch("cherrypy.engine.publish")
    def test_unmuted_when_not_scheduled(self, publish_mock: mock.Mock) -> None:
        """Not muted by schedule if no schedules are in range."""

        def side_effect(*args: str, **_: str) -> Any:
            if args[0] == "registry:search:valuelist":
                return ["11:00 PM\n9:00 AM"]
            if args[0] == "clock:scheduled":
                return [False]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        result = self.plugin.muted_by_schedule()

        self.assertFalse(result)

    @mock.patch("cherrypy.engine.publish")
    def test_muted_temporarily(self, publish_mock: mock.Mock) -> None:
        """Muted temporarily if registry says so."""

        def side_effect(*args: str, **_: str) -> Any:
            print(args)
            if args[0] == "registry:first:value":
                return [1]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        result = self.plugin.muted_temporarily()
        self.assertTrue(result)

    @mock.patch("cherrypy.engine.publish")
    def test_not_muted_temporarily(self, publish_mock: mock.Mock) -> None:
        """Not muted temporarily if registry doesn't say so."""

        def side_effect(*args: str, **_: str) -> Any:
            print(args)
            if args[0] == "registry:first:value":
                return [None]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        result = self.plugin.muted_temporarily()
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
