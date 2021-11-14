"""Test suite for the grids app."""

from datetime import datetime
import typing
import unittest
from unittest import mock
from testing.assertions import ResponseAssertions
from testing import helpers
from testing.cptestcase import BaseCherryPyTestCase
import apps.grids.main  # type: ignore


class TestGrids(BaseCherryPyTestCase, ResponseAssertions):
    """Tests for the application controller."""

    @classmethod
    def setUpClass(cls) -> None:
        helpers.start_server(apps.grids.main.Controller)

    @classmethod
    def tearDownClass(cls) -> None:
        helpers.stop_server()

    def test_allow(self) -> None:
        """Verify the controller's supported HTTP methods"""
        response = self.request("/", method="HEAD")
        self.assert_allowed(response, ("GET",))

    def test_exposed(self) -> None:
        """The application is publicly available."""
        self.assert_exposed(apps.grids.main.Controller)

    def test_show_on_homepage(self) -> None:
        """The application is displayed in the homepage app."""
        self.assert_show_on_homepage(apps.grids.main.Controller)

    @mock.patch("cherrypy.engine.publish")
    def test_month_layout(self, publish_mock: mock.Mock) -> None:
        """The first two columns of a template with layout=month are Date and
        Day, even though these are not otherwise specified in the template"""

        def side_effect(*args: str, **_: str) -> typing.Any:
            """Side effects local function"""
            if args[0] == "registry:first:value":
                return ["Column 1, Column 2, Column 3\nlayout=month"]
            if args[0] == "clock:from_format":
                return [datetime.now()]
            if args[0] == "clock:now":
                return [datetime.now()]
            if args[0] == "jinja:render":
                return [""]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        self.request("/test1")

        self.assertCountEqual(
            helpers.template_var(publish_mock, "headers"),
            ['Date', 'Day', 'Column 1', 'Column 2', 'Column 3']
        )

    @mock.patch("cherrypy.engine.publish")
    def test_invalid_start(self, publish_mock: mock.Mock) -> None:
        """An invalid start date for a monthly layout is handled gracefully"""

        def side_effect(*args: str, **_: str) -> typing.Any:
            """Side effects local function"""
            if args[0] == "registry:first:value":
                return ["Column 4, Column 5, Column 6\nlayout=month"]
            if args[0] == "clock:from_format":
                return [None]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        response = self.request("/test1", start="1234-56")

        self.assert_status(response, 400)

    @mock.patch("cherrypy.engine.publish")
    def test_invalid_grid(self, publish_mock: mock.Mock) -> None:
        """An invalid grid name is handled gracefully"""

        def side_effect(*args: str, **_: str) -> typing.Any:
            """Side effects local function"""
            if args[0] == "registry:first:value":
                return [None]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        response = self.request("/invalid")

        self.assert_status(response, 404)


if __name__ == "__main__":
    unittest.main()
