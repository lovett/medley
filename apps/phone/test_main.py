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
    Tests for the phone application controller
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
        self.assertAllowedMethods(response, ("GET",))

    @mock.patch("cherrypy.tools.negotiable._renderHtml")
    @mock.patch("cherrypy.engine.publish")
    def test_no_number(self, publish_mock, render_mock):
        """An HTML request with no number displays the search form"""

        def side_effect(*args, **_):
            """Side effects local function"""
            if args[0] == "phone:sanitize":
                return [None]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect
        self.request("/")
        self.assertFalse(helpers.html_var(render_mock, "error"))

    @mock.patch("cherrypy.tools.negotiable._renderHtml")
    @mock.patch("cherrypy.engine.publish")
    def test_invalid_number_as_html(self, publish_mock, render_mock):
        """An HTML request with an invalid number redirects with a message"""

        def side_effect(*args, **_):
            """Side effects local function"""
            if args[0] == "phone:sanitize":
                return [None]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect
        self.request("/", number="invalid-number-html")
        self.assertTrue(helpers.html_var(render_mock, "error"))

    @mock.patch("cherrypy.engine.publish")
    def test_invalid_number_as_json(self, publish_mock):
        """A JSON request with an invalid number returns an error"""

        def side_effect(*args, **_):
            """Side effects local function"""
            if args[0] == "phone:sanitize":
                return [None]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect
        response = self.request(
            "/",
            number="invalid-number-json",
            as_json=True
        )
        self.assertTrue(helpers.response_is_json(response))
        self.assertTrue("error" in response.body)

    @mock.patch("cherrypy.engine.publish")
    def test_invalid_number_as_text(self, publish_mock):
        """A text/plain request with an invalid number returns an error"""

        def side_effect(*args, **_):
            """Side effects local function"""
            if args[0] == "phone:sanitize":
                return [None]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect
        response = self.request(
            "/",
            number="invalid-number-text",
            as_text=True
        )
        self.assertTrue(helpers.response_is_text(response))
        self.assertEqual(
            response.body,
            apps.phone.main.Controller.messages["invalid"]
        )

    @mock.patch("cherrypy.tools.negotiable._renderHtml")
    @mock.patch("cherrypy.engine.publish")
    def test_valid_number(self, publish_mock, render_mock):
        """A valid number lookup performs a state abbreviation lookup"""
        def side_effect(*args, **_):
            """Side effects local function"""
            value_map = {
                "cache:get": [None],
                "asterisk:get_caller_id": [None],
                "geography:state_by_area_code": [
                    (None, "XY", None)
                ],
                "geography:unabbreviate_state": [
                    (None, "Unabbreviated State")
                ],
                "phone:sanitize": ["1234567890"],
                "asterisk:is_blacklisted": [False],
                "cdr:call_history": [[]],
            }

            return value_map.get(args[0], mock.DEFAULT)

        publish_mock.side_effect = side_effect
        self.request("/", number="1234567890")
        self.assertEqual(
            helpers.html_var(render_mock, "state_abbreviation"),
            "XY"
        )

    @mock.patch("cherrypy.tools.negotiable._renderHtml")
    @mock.patch("cherrypy.engine.publish")
    def test_valid_number_cached(self, publish_mock, render_mock):
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
            if args[0] == "phone:sanitize":
                return ["1234567890"]
            if args[0] == "asterisk:is_blacklisted":
                return [False]
            if args[0] == "asterisk:get_caller_id":
                return [None]
            if args[0] == "cdr:call_history":
                return [[[{"clid": "test"}]]]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect
        self.request("/", number="1234567890")
        self.assertEqual(
            helpers.html_var(render_mock, "state_abbreviation"),
            "XY"
        )


if __name__ == "__main__":
    unittest.main()
