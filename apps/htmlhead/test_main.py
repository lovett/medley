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


class TestHeaders(BaseCherryPyTestCase, ResponseAssertions):
    """
    Tests for the htmlhead application controller
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
        self.assertAllowedMethods(response, ("GET",))

    @mock.patch("cherrypy.tools.negotiable.render_html")
    @mock.patch("cherrypy.engine.publish")
    def test_default(self, publish_mock, render_mock):
        """The default view is a form to enter a URL."""

        def side_effect(*args, **_):
            """Side effects local function"""

            if args[0] == "url:internal":
                return ["/"]
            return mock.DEFAULT
        publish_mock.side_effect = side_effect

        response = self.request("/")

        self.assertEqual(
            helpers.html_var(render_mock, "app_url"),
            "/"
        )

        self.assertEqual(
            helpers.html_var(render_mock, "tags"),
            []
        )

        self.assertIsNone(helpers.html_var(render_mock, "url"))

        self.assertEqual(response.code, 200)

    @mock.patch("cherrypy.tools.negotiable.render_html")
    @mock.patch("cherrypy.engine.publish")
    @responses.activate
    def test_with_url(self, publish_mock, render_mock):
        """When a URL is provided, it is parsed for tags in the head."""

        def side_effect(*args, **_):
            """Side effects local function"""

            if args[0] == "url:internal":
                return ["/"]
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
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        self.request("/", url="http://example.com")

        self.assertEqual(
            helpers.html_var(render_mock, "tags"),
            [('title', [], 'Hello world')]
        )

    @mock.patch("cherrypy.tools.negotiable.render_html")
    @mock.patch("cherrypy.engine.publish")
    @responses.activate
    def test_404(self, publish_mock, render_mock):
        """When a URL is provided, it is parsed for tags in the head."""

        def side_effect(*args, **_):
            """Side effects local function"""

            if args[0] == "url:internal":
                return ["/"]
            if args[0] == "urlfetch:get":
                responses.add(
                    responses.GET,
                    "http://example.com",
                    status=404
                )
                response = requests.get("http://example.com")
                return [response]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        self.request("/", url="http://example.com")

        self.assertEqual(
            helpers.html_var(render_mock, "status_code"),
            404
        )


if __name__ == "__main__":
    unittest.main()
