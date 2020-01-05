"""
Test suite for the phone app
"""

import unittest
import mock
from testing.assertions import ResponseAssertions
from testing import helpers
from testing.cptestcase import BaseCherryPyTestCase
import apps.phone.main


class TestPhone(BaseCherryPyTestCase, ResponseAssertions):
    """
    Tests for the application controller.
    """

    @classmethod
    def setUpClass(cls):
        """Start a faux cherrypy server"""
        helpers.start_server(apps.phone.main.Controller)

    @classmethod
    def tearDownClass(cls):
        """Shut down the faux server"""
        helpers.stop_server()

    def test_allow(self):
        """Verify the controller's supported HTTP methods"""
        response = self.request("/", method="HEAD")
        self.assert_allowed(response, ("GET",))

    def test_exposed(self):
        """The application is publicly available."""
        self.assert_exposed(apps.phone.main.Controller)

    def test_show_on_homepage(self):
        """The application is displayed in the homepage app."""
        self.assert_show_on_homepage(apps.phone.main.Controller)

    @mock.patch("cherrypy.engine.publish")
    def test_no_number(self, publish_mock):
        """An HTML request with no number displays the search form"""

        def side_effect(*args, **_):
            """Side effects local function"""
            if args[0] == "formatting:phone_sanitize":
                return [None]
            if args[0] == "jinja:render":
                return [""]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect
        self.request("/")
        self.assertIsNone(
            publish_mock.call_args_list[-1].kwargs.get("error"),
        )

    @mock.patch("cherrypy.engine.publish")
    def test_invalid_number_as_html(self, publish_mock):
        """An HTML request with an invalid number redirects with a message"""

        def side_effect(*args, **_):
            """Side effects local function"""
            if args[0] == "formatting:phone_sanitize":
                return [None]
            if args[0] == "jinja:render":
                return [""]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect
        self.request("/", number="invalid-number-html")
        self.assertNotEqual(
            publish_mock.call_args_list[-1].kwargs.get("error"),
            ""
        )

    @mock.patch("cherrypy.engine.publish")
    def test_valid_number(self, publish_mock):
        """A valid number lookup performs a state abbreviation lookup"""
        def side_effect(*args, **_):
            """Side effects local function"""
            value_map = {
                "cache:get": [None],
                "geography:state_by_area_code": [
                    (None, "XY", None)
                ],
                "geography:unabbreviate_state": [
                    (None, "Unabbreviated State")
                ],
                "formatting:phone_sanitize": ["1234567890"],
                "cdr:call_history": [[]],
            }
            if args[0] == "jinja:render":
                return [""]

            return value_map.get(args[0], mock.DEFAULT)

        publish_mock.side_effect = side_effect
        self.request("/", number="1234567890")
        self.assertEqual(
            publish_mock.call_args_list[-1].kwargs.get("state_abbreviation"),
            "XY"
        )

    @mock.patch("cherrypy.engine.publish")
    def test_valid_number_cached(self, publish_mock):
        """Successful number lookups are cached"""
        def side_effect(*args, **_):
            """Side effects local function"""
            if args[0] == "cache:get":
                return [{
                    "state_lookup": ("query placeholder", "XY", None),
                    "state_name_lookup": (
                        "query placeholder",
                        "Unabbreviated State"
                    )
                }]
            if args[0] == "formatting:phone_sanitize":
                return ["1234567890"]
            if args[0] == "cdr:call_history":
                return [[{"clid": "test"}]]
            if args[0] == "jinja:render":
                return [""]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect
        self.request("/", number="1234567890")
        self.assertEqual(
            publish_mock.call_args_list[-1].kwargs.get("state_abbreviation"),
            "XY"
        )


if __name__ == "__main__":
    unittest.main()
