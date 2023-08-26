"""Test suite for the headlines app."""

from typing import Any
import unittest
from unittest import mock
from testing.assertions import ResponseAssertions
from testing import helpers
from testing.cptestcase import BaseCherryPyTestCase
import apps.headlines.main  # type: ignore


class TestHeadlines(BaseCherryPyTestCase, ResponseAssertions):
    """
    Tests for the application controller.
    """

    @classmethod
    def setUpClass(cls) -> None:
        """Start a faux cherrypy server."""
        helpers.start_server(apps.headlines.main.Controller)

    @classmethod
    def tearDownClass(cls) -> None:
        """Shut down the faux server."""
        helpers.stop_server()

    def test_allow(self) -> None:
        """Verify the controller's supported HTTP methods"""

    def test_exposed(self) -> None:
        """The application is publicly available."""
        self.assert_exposed(apps.headlines.main.Controller)

    def test_show_on_homepage(self) -> None:
        """The application is displayed in the homepage app."""
        self.assert_show_on_homepage(apps.headlines.main.Controller)

        response = self.request("/", method="HEAD")
        self.assert_allowed(response, ("GET",))

    @mock.patch("cherrypy.engine.publish")
    def test_cache_hit_bypasses_fetch(self, publish_mock: mock.Mock) -> None:
        """If headlines have been cached, urlfetch does not occur."""

        def side_effect(*args: str, **_kwargs: str) -> Any:
            if args[0] == "clock:day:remaining":
                return [1]
            if args[0] == "jinja:render":
                return [""]

            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        self.request("/")

        self.assertIsNone(
            helpers.find_publish_call(publish_mock, "urlfetch:get:json")
        )

        self.assertIsNone(
            helpers.find_publish_call(publish_mock, "cache:set")
        )

    @mock.patch("cherrypy.engine.publish")
    def test_cache_miss_triggers_fetch(self, publish_mock: mock.Mock) -> None:
        """A urlfetch occurs when a cached value is not present"""

        def side_effect(*args: str, **kwargs: str) -> Any:
            if args[0] == "clock:day:remaining":
                return [1]
            if "key" in kwargs and kwargs["key"] == "newsapi:*":
                return [{
                    "country": "us",
                    "key": "testkey",
                    "category": ["category1", "category2", "category3"]
                }]

            if args[0] == "jinja:render":
                return [""]

            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        self.request("/")

        self.assertIsNotNone(
            helpers.find_publish_call(publish_mock, "urlfetch:get:json")
        )

    @mock.patch("cherrypy.engine.publish")
    def test_fetch_failure(self, publish_mock: mock.Mock) -> None:
        """An error is returned if the url fetch fails."""

        def side_effect(*args: str, **kwargs: str) -> Any:
            if args[0] == "clock:day:remaining":
                return [1]
            if "key" in kwargs and kwargs["key"] == "newsapi:*":
                return [{
                    "country": "us",
                    "key": "testkey",
                    "category": ["category1", "category2", "category3"]
                }]

            if args[0] == "urlfetch:get:json":
                return [(None, None)]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        response = self.request("/")

        self.assertEqual(response.code, 503)

    @mock.patch("cherrypy.engine.publish")
    def test_cache_header(self, publish_mock: mock.Mock) -> None:
        """The response sends a Cache-Control header."""

        def side_effect(*args: str, **_: str) -> Any:
            if args[0] == "clock:day:remaining":
                return [1]
            if args[0] == "urlfetch:get:json":
                return [(None, None)]
            if args[0] == "jinja:render":
                return [""]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        response = self.request("/")
        self.assertIsNotNone(response.headers.get("Cache-Control"))


if __name__ == "__main__":
    unittest.main()
