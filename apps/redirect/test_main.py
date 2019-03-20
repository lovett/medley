"""
Test suite for the redirect app
"""

import unittest
import mock
from testing.assertions import ResponseAssertions
from testing import helpers
from testing.cptestcase import BaseCherryPyTestCase
import apps.redirect.main


class TestRedirect(BaseCherryPyTestCase, ResponseAssertions):
    """
    Tests for the redirect application controller
    """

    @classmethod
    def setUpClass(cls):
        """Start a faux cherrypy server"""
        helpers.start_server(apps.redirect.main.Controller)

    @classmethod
    def tearDownClass(cls):
        """Shut down the faux server"""
        helpers.stop_server()

    def test_allow(self):
        """Verify the controller's supported HTTP methods"""
        response = self.request("/", method="HEAD")
        self.assertAllowedMethods(response, ("GET",))

    @mock.patch("cherrypy.tools.negotiable.render_html")
    def test_no_destination(self, render_mock):
        """If no URL is provided, no redirect occurs."""
        self.request("/")

        self.assertEqual(
            helpers.html_var(render_mock, "app_name"),
            apps.redirect.main.Controller.name
        )

        self.assertIsNone(
            helpers.html_var(render_mock, "dest")
        )

    @mock.patch("cherrypy.tools.negotiable.render_html")
    def test_encoded_destination(self, render_mock):
        """Encoded URLs are decoded."""

        self.request("/", u="http%3A%2F%2Fexample.com")

        self.assertEqual(
            helpers.html_var(render_mock, "app_name"),
            apps.redirect.main.Controller.name
        )

        self.assertEqual(
            helpers.html_var(render_mock, "dest"),
            "http://example.com"
        )

    @mock.patch("cherrypy.tools.negotiable.render_html")
    def test_unencoded_destination(self, render_mock):
        """Unencoded URLs are used as-is."""

        self.request("/", u="http://example.net")

        self.assertEqual(
            helpers.html_var(render_mock, "app_name"),
            apps.redirect.main.Controller.name
        )

        self.assertEqual(
            helpers.html_var(render_mock, "dest"),
            "http://example.net"
        )

    @mock.patch("cherrypy.tools.negotiable.render_html")
    def test_encoded_querystring(self, render_mock):
        """URL decoding preserves querystring values."""

        self.request(
            "/",
            u="http%3A%2F%2Fexample.com%3Fhello%3Dworld"
        )

        self.assertEqual(
            helpers.html_var(render_mock, "app_name"),
            apps.redirect.main.Controller.name
        )

        self.assertEqual(
            helpers.html_var(render_mock, "dest"),
            "http://example.com?hello=world"
        )


if __name__ == "__main__":
    unittest.main()
