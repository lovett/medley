"""Test suite for the calls app."""

import typing
import unittest
from unittest import mock
from testing.assertions import ResponseAssertions
from testing import helpers
from testing.cptestcase import BaseCherryPyTestCase
import apps.calls.main  # type: ignore


class TestCalls(BaseCherryPyTestCase, ResponseAssertions):
    """Tests for the application controller."""

    @classmethod
    def setUpClass(cls) -> None:
        """Start a faux cherrypy server"""
        helpers.start_server(apps.calls.main.Controller)

    @classmethod
    def tearDownClass(cls) -> None:
        """Shut down the faux server"""
        helpers.stop_server()

    def test_allow(self) -> None:
        """Verify the controller's supported HTTP methods"""
        response = self.request("/", method="HEAD")
        self.assert_allowed(response, ("GET",))

    def test_exposed(self) -> None:
        """The application is publicly available."""
        self.assert_exposed(apps.calls.main.Controller)

    def test_show_on_homepage(self) -> None:
        """The application is displayed in the homepage app."""
        self.assert_show_on_homepage(apps.calls.main.Controller)

    @mock.patch("cherrypy.engine.publish")
    def test_exclusion(self, publish_mock: mock.Mock) -> None:
        """Source and destination numbers are skipped"""
        def side_effect(*args: str, **_: str) -> typing.Any:
            """Side effects local function"""
            if args[0] == "registry:search":
                return [(2, (
                    {"key": "src", "value": "test"},
                    {"key": "dst", "value": "test2"}
                ))]

            if args[0] == "jinja:render":
                return [""]

            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        self.request("/")

        publish_mock.assert_any_call(
            "cdr:timeline",
            dst_exclude=["test2"],
            limit=50,
            offset=0,
            src_exclude=["test"]
        )


if __name__ == "__main__":
    unittest.main()
