"""Test suite for the phone app."""

import typing
import unittest
from unittest import mock
from testing.assertions import ResponseAssertions
from testing import helpers
from testing.cptestcase import BaseCherryPyTestCase
import apps.phone.main  # type: ignore


class TestPhone(BaseCherryPyTestCase, ResponseAssertions):
    """
    Tests for the application controller.
    """

    @classmethod
    def setUpClass(cls) -> None:
        """Start a faux cherrypy server"""
        helpers.start_server(apps.phone.main.Controller)

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
        self.assert_exposed(apps.phone.main.Controller)

    def test_show_on_homepage(self) -> None:
        """The application is displayed in the homepage app."""
        self.assert_show_on_homepage(apps.phone.main.Controller)

    @mock.patch("cherrypy.engine.publish")
    def test_no_number(self, publish_mock: mock.Mock) -> None:
        """An HTML request with no number displays the search form"""

        def side_effect(*args: str, **_: str) -> typing.Any:
            """Side effects local function"""
            if args[0] == "jinja:render":
                return [""]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect
        self.request("/")
        self.assertIsNone(
            helpers.template_var(publish_mock, "error"),
        )

    @mock.patch("cherrypy.engine.publish")
    def test_invalid_number_as_html(self, publish_mock: mock.Mock) -> None:
        """An HTML request with an invalid number redirects with a message"""

        def side_effect(*args: str, **_: str) -> typing.Any:
            """Side effects local function"""
            if args[0] == "jinja:render":
                return [""]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect
        self.request("/", number="invalid-number-html")
        self.assertNotEqual(
            helpers.template_var(publish_mock, "error"),
            ""
        )

    @mock.patch("cherrypy.engine.publish")
    def test_valid_number(self, publish_mock: mock.Mock) -> None:
        """A valid number lookup performs a state abbreviation lookup"""
        def side_effect(*args: str, **_: str) -> typing.Any:
            """Side effects local function"""
            value_map = {
                "cache:get": [None],
                "geography:state_by_area_code": [
                    (None, "XY", None)
                ],
                "geography:unabbreviate_state": [
                    (None, "Unabbreviated State")
                ],
                "cdr:history": [([], 0)],
            }
            if args[0] == "jinja:render":
                return [""]

            return value_map.get(args[0], mock.DEFAULT)

        publish_mock.side_effect = side_effect
        self.request("/", number="1234567890")
        self.assertEqual(
            helpers.template_var(publish_mock, "state_abbreviation"),
            "XY"
        )

    @mock.patch("cherrypy.engine.publish")
    def test_valid_number_cached(self, publish_mock: mock.Mock) -> None:
        """Successful number lookups are cached"""
        def side_effect(*args: str, **_: str) -> typing.Any:
            """Side effects local function"""
            if args[0] == "cache:get":
                return [{
                    "state_lookup": ("query placeholder", "XY", None),
                    "state_name_lookup": (
                        "query placeholder",
                        "Unabbreviated State"
                    )
                }]
            if args[0] == "cdr:history":
                return [[{"clid": "test"}, 1]]
            if args[0] == "jinja:render":
                return [""]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect
        self.request("/", number="1234567890")
        self.assertEqual(
            helpers.template_var(publish_mock, "state_abbreviation"),
            "XY"
        )


if __name__ == "__main__":
    unittest.main()
