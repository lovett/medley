"""Test suite for the logindex app."""

from datetime import datetime
import unittest
from unittest import mock
import typing
import pytz
from testing.assertions import ResponseAssertions
from testing import helpers
from testing.cptestcase import BaseCherryPyTestCase
import apps.logindex.main  # type: ignore


class TestLater(BaseCherryPyTestCase, ResponseAssertions):
    """
    Tests for the application controller.
    """

    @classmethod
    def setUpClass(cls) -> None:
        """Start a faux cherrypy server"""
        helpers.start_server(apps.logindex.main.Controller)

    @classmethod
    def tearDownClass(cls) -> None:
        """Shut down the faux server"""
        helpers.stop_server()

    def test_allow(self) -> None:
        """Verify the controller's supported HTTP methods"""
        response = self.request("/", method="HEAD")
        self.assert_allowed(response, ("POST",))

    def test_exposed(self) -> None:
        """The application is publicly available."""
        self.assert_exposed(apps.logindex.main.Controller)

    def test_not_show_on_homepage(self) -> None:
        """The application is not displayed in the homepage app."""
        self.assert_not_show_on_homepage(apps.logindex.main.Controller)

    @mock.patch("cherrypy.engine.publish")
    def test_invalid_start(self, publish_mock: mock.Mock) -> None:
        """An error should be thrown if the start date cannot be parsed"""
        def side_effect(*args: str, **_kwargs: str) -> typing.Any:
            """Side effects local function"""
            print(args)
            if args[0] == "clock:from_format":
                return [None]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        response = self.request(
            "/",
            method="POST",
            start="invalid"
        )
        self.assertEqual(response.code, 400)

    @mock.patch("cherrypy.engine.publish")
    def test_invalid_end(self, publish_mock: mock.Mock) -> None:
        """An error should be thrown if the end date cannot be parsed"""

        def side_effect(*args: str, **_kwargs: str) -> typing.Any:
            """Side effects local function"""
            print(args)
            if args[0] == "clock:from_format":
                if args[1] == "2000-01-01":
                    return [
                        datetime(2000, 1, 1, tzinfo=pytz.timezone("UTC"))
                    ]
                if args[1] == "1999-12-31":
                    return [
                        datetime(1999, 12, 31, tzinfo=pytz.timezone("UTC"))
                    ]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        response = self.request(
            "/",
            method="POST",
            start="2000-01-01.log",
            end="1999-12-31.log"
        )
        self.assertEqual(response.code, 400)

    @mock.patch("cherrypy.engine.publish")
    def test_valid_range(self, publish_mock: mock.Mock) -> None:
        """The logindex plugin is called when a valid time range is given."""

        def side_effect(*args: str, **_kwargs: str) -> typing.Any:
            """Side effects local function"""
            if args[0] == "clock:from_format":
                if args[1] == "2017-01-01":
                    return [datetime(2017, 1, 1, tzinfo=pytz.timezone("UTC"))]
                if args[1] == "2017-01-03":
                    return [datetime(2017, 1, 3, tzinfo=pytz.timezone("UTC"))]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        self.request(
            "/",
            method="POST",
            start="2017-01-01.log",
            end="2017-01-03.log"
        )

        self.assertEqual(
            helpers.find_publish_call(publish_mock, "logindex:enqueue"),
            mock.call(
                "logindex:enqueue",
                datetime(2017, 1, 1, 0, 0, tzinfo=pytz.timezone("UTC")),
                datetime(2017, 1, 3, 0, 0, tzinfo=pytz.timezone("UTC"))
            )
        )

    @mock.patch("cherrypy.engine.publish")
    def test_only_start(self, publish_mock: mock.Mock) -> None:
        """
        A single-day time range can be specified by only specifying the
        start date.
        """

        def side_effect(*args: str, **_kwargs: str) -> typing.Any:
            """Side effects local function"""
            if args[0] == "clock:from_format":
                return [datetime(2017, 1, 1, tzinfo=pytz.timezone("UTC"))]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        self.request(
            "/",
            method="POST",
            start="2017-01-01.log"
        )

        enqueue_call = helpers.find_publish_call(
            publish_mock,
            "logindex:enqueue"
        )

        start = datetime(2017, 1, 1, 0, 0, tzinfo=pytz.timezone("UTC"))

        mock_call = mock.call("logindex:enqueue", start, start)

        print(enqueue_call)
        print(mock_call)

        self.assertEqual(
            enqueue_call,
            mock_call
        )


if __name__ == "__main__":
    unittest.main()
