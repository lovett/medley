"""
Test suite for the whois app
"""

import unittest
import mock
from testing.assertions import ResponseAssertions
from testing import helpers
from testing.cptestcase import BaseCherryPyTestCase
import apps.headers.main


class TestHeaders(BaseCherryPyTestCase, ResponseAssertions):
    """
    Tests for the application controller.
    """

    @classmethod
    def setUpClass(cls):
        """Start a faux cherrypy server"""
        helpers.start_server(apps.headers.main.Controller)

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
        self.assert_exposed(apps.headers.main.Controller)

    def test_show_on_homepage(self):
        """The application is displayed in the homepage app."""
        self.assert_show_on_homepage(apps.headers.main.Controller)

    @mock.patch("cherrypy.engine.publish")
    def test_returns_html(self, publish_mock):
        """GET returns text/html by default"""

        def side_effect(*args, **_):
            """Side effects local function"""
            if args[0] == "jinja:render":
                return [""]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        self.request("/", headers={
            "X-Test": "Hello"
        })

        self.assertIn(
            ("X-Test", "Hello"),
            publish_mock.call_args_list[-1].kwargs.get("headers")
        )

    def test_returns_json(self):
        """GET returns application/json if requested"""
        response = self.request("/", as_json=True)
        self.assertEqual(response.code, 200)
        self.assert_json(response)

    def test_returns_text(self):
        """GET returns text/plain if requested"""
        response = self.request("/", as_text=True)
        self.assertEqual(response.code, 200)
        self.assert_text(response)

    def test_custom_header(self):
        """GET recognizes custom headers"""

        response = self.request(
            "/",
            headers={"Special_Header": "Special Value"},
            as_json=True
        )

        print(response.body)
        _, value = next(
            pair
            for pair in response.body
            if pair[0] == "Special_Header"
        )

        self.assertEqual(value, "Special Value")


if __name__ == "__main__":
    unittest.main()
