"""
Test suite for the whois app
"""

import unittest
from testing.assertions import ResponseAssertions
from testing import helpers
from testing.cptestcase import BaseCherryPyTestCase
import apps.headers.main


class TestHeaders(BaseCherryPyTestCase, ResponseAssertions):
    """
    Tests for the whois application controller
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

    def test_returns_html(self):
        """GET returns text/html by default"""
        response = self.request("/")
        self.assert_html(response, "<table")

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

        _, value = next(
            pair
            for pair in response.body
            if pair[0] == "Special_Header"
        )
        self.assertEqual(value, "Special Value")


if __name__ == "__main__":
    unittest.main()
