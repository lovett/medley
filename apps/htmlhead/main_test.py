"""
Test suite for the htmlhead app
"""

import unittest
import mock
import requests
import responses
from testing.assertions import ResponseAssertions
from testing import helpers
from testing.cptestcase import BaseCherryPyTestCase
import apps.htmlhead.main


class TestHtmlhead(BaseCherryPyTestCase, ResponseAssertions):
    """
    Tests for the application controller.
    """

    @classmethod
    def setUpClass(cls):
        """Start a faux cherrypy server"""
        helpers.start_server(apps.htmlhead.main.Controller)

    @classmethod
    def tearDownClass(cls):
        """Shut down the faux server"""
        helpers.stop_server()

    def test_allow(self):
        """Verify the controller's supported HTTP methods"""
        response = self.request("/", method="HEAD")
        self.assert_allowed(response, ("GET", "POST"))

    def test_exposed(self):
        """The application is publicly available."""
        self.assert_exposed(apps.htmlhead.main.Controller)

    def test_show_on_homepage(self):
        """The application is displayed in the homepage app."""
        self.assert_show_on_homepage(apps.htmlhead.main.Controller)

    @mock.patch("cherrypy.engine.publish")
    @responses.activate
    def test_with_url(self, publish_mock):
        """When a URL is provided, it is parsed for tags in the head."""

        def side_effect(*args, **_):
            """Side effects local function"""

            if args[0] == "urlfetch:get":
                responses.add(
                    responses.GET,
                    "http://example.com",
                    body="""
                    <html>
                    <head><title>Hello world</title></head>
                    </html>
                    """
                )
                response = requests.get("http://example.com")
                return [response]
            if args[0] == "jinja:render":
                return [""]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        self.request("/", url="http://example.com", method="post")

        self.assertEqual(
            publish_mock.call_args_list[-1].kwargs.get("tags"),
            [('title', [], 'Hello world')]
        )

    @mock.patch("cherrypy.engine.publish")
    @responses.activate
    def test_404(self, publish_mock):
        """When a URL is provided, it is parsed for tags in the head."""

        def side_effect(*args, **_):
            """Side effects local function"""

            if args[0] == "urlfetch:get":
                responses.add(
                    responses.GET,
                    "http://example.com",
                    status=404
                )
                response = requests.get("http://example.com")
                return [response]
            if args[0] == "jinja:render":
                return [""]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        self.request("/", url="http://example.com", method="post")

        self.assertEqual(
            publish_mock.call_args_list[-1].kwargs.get("status_code"),
            404
        )


if __name__ == "__main__":
    unittest.main()
