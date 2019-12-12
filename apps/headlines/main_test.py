"""
Test suite for the headlines app.
"""

import unittest
import mock
from testing.assertions import ResponseAssertions
from testing import helpers
from testing.cptestcase import BaseCherryPyTestCase
import apps.headlines.main


class TestHeadlines(BaseCherryPyTestCase, ResponseAssertions):
    """
    Tests for the application controller.
    """

    @classmethod
    def setUpClass(cls):
        """Start a faux cherrypy server."""
        helpers.start_server(apps.headlines.main.Controller)

    @classmethod
    def tearDownClass(cls):
        """Shut down the faux server."""
        helpers.stop_server()

    def test_allow(self):
        """Verify the controller's supported HTTP methods"""

    def test_exposed(self):
        """The application is publicly available."""
        self.assert_exposed(apps.headlines.main.Controller)

    def test_show_on_homepage(self):
        """The application is displayed in the homepage app."""
        self.assert_show_on_homepage(apps.headlines.main.Controller)

        response = self.request("/", method="HEAD")
        self.assert_allowed(response, ("GET",))

    @mock.patch("cherrypy.engine.publish")
    def test_cache_miss_triggers_fetch(self, publish_mock):
        """A urlfetch occurs when a cached value is not present"""

        def side_effect(*args, **kwargs):
            """Side effects local function"""
            if "key" in kwargs and kwargs["key"] == "newsapi:*":
                return [{
                    "country": "us",
                    "key": "testkey",
                    "category": ["category1", "category2", "category3"]
                }]
            if args[0] == "cache:get":
                return [None]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        self.request("/")

        publish_calls = [args[0][0] for args in publish_mock.call_args_list]

        print(publish_calls)

        self.assertTrue("urlfetch:get" in publish_calls)
        self.assertTrue("cache:set" in publish_calls)

    @mock.patch("cherrypy.engine.publish")
    def test_fetch_failure(self, publish_mock):
        """An error is returned if the url fetch fails."""

        def side_effect(*args, **kwargs):
            """Side effects local function"""
            if "key" in kwargs and kwargs["key"] == "newsapi:*":
                return [{
                    "country": "us",
                    "key": "testkey",
                    "category": ["category1", "category2", "category3"]
                }]

            if args[0] in ("cache:get", "urlfetch:get"):
                return [None]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        response = self.request("/")

        self.assertEqual(response.code, 503)

    @mock.patch("cherrypy.engine.publish")
    def test_cache_header(self, publish_mock):
        """The response sends a Cache-Control header."""

        def side_effect(*args, **_):
            """Side effects local function"""
            if args[0] in ("cache:get", "urlfetch:get"):
                return [None]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        response = self.request("/")
        self.assertIsNotNone(response.headers.get("Cache-Control"))


if __name__ == "__main__":
    unittest.main()
