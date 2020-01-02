"""
Test suite for the later app
"""

import unittest
import mock
from testing.assertions import ResponseAssertions
from testing import helpers
from testing.cptestcase import BaseCherryPyTestCase
import apps.later.main


class TestLater(BaseCherryPyTestCase, ResponseAssertions):
    """
    Tests for the application controller.
    """

    @classmethod
    def setUpClass(cls):
        helpers.start_server(apps.later.main.Controller)

    @classmethod
    def tearDownClass(cls):
        helpers.stop_server()

    def xtest_allow(self):
        """Verify the controller's supported HTTP methods"""
        response = self.request("/", method="HEAD")
        self.assert_allowed(response, ("GET",))

    def xtest_exposed(self):
        """The application is publicly available."""
        self.assert_exposed(apps.later.main.Controller)

    def xtest_show_on_homepage(self):
        """The application is displayed in the homepage app."""
        self.assert_show_on_homepage(apps.later.main.Controller)

    def xtest_populates_title(self):
        """The title field is prepopulated if provided via querystring"""

        samples = (
            ("It's a <i>sample</i> title", "It&#39;s a sample title")
        )

        for sample in samples:
            response = self.request("/", title=sample[0])
            self.assertTrue(sample[1] in response.body)

    @mock.patch("cherrypy.engine.publish")
    def test_populates_tags(self, publish_mock):
        """The tags field is prepopulated if provided via querystring"""

        def side_effect(*args, **_):
            """Side effects local function"""
            if args[0].startswith("markup:"):
                return ["abc123"]

            if args[0] == "jinja:render":
                return [""]

            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        self.request("/", tags="hello")

        self.assertEqual(
            publish_mock.call_args_list[-1].kwargs.get("tags"),
            "abc123"
        )

    @mock.patch("cherrypy.engine.publish")
    def test_populates_comments(self, publish_mock):
        """The comments field is prepopulated if provided via querystring

        A period is also added to make the populated value a sentence.
        """
        def side_effect(*args, **_):
            """Side effects local function"""
            if args[0].startswith("markup:"):
                return ["This is sentence 1. this is sentence 2"]
            if args[0] == "jinja:render":
                return [""]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        self.request("/", comments="hello")

        self.assertEqual(
            publish_mock.call_args_list[-1].kwargs.get("comments"),
            "This is sentence 1. This is sentence 2."
        )

    @mock.patch("cherrypy.engine.publish")
    def test_ignores_reddit_comment(self, publish_mock):
        """The comments field of a reddit.com URL is discarded if it came from
        a meta tag."""

        def side_effect(*args, **_):
            """Side effects local function"""
            if args[0].startswith("markup:"):
                return [args[1]]
            if args[0] == "bookmarks:find":
                return [{
                    "title": "existing title",
                    "tags": None,
                    "comments": None
                }]
            if args[0] == "jinja:render":
                return [""]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        self.request(
            "/",
            url="http://reddit.com",
            comments="r/subredditname: Lorem ipsum"
        )

        self.assertIsNone(
            publish_mock.call_args_list[-1].kwargs.get("comments")
        )

    @mock.patch("cherrypy.engine.publish")
    def test_url_lookup(self, publish_mock):
        """An existing bookmark is fetched by url, overwriting querystring
        values

        """

        def side_effect(*args, **_):
            """Side effects local function"""
            if args[0].startswith("markup:"):
                return [args[1]]
            if args[0] == "bookmarks:find":
                return [{
                    "title": "existing title",
                    "tags": None,
                    "comments": None
                }]
            if args[0] == "jinja:render":
                return [""]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        self.request("/", url="http://example.com", title="my title")

        self.assertEqual(
            publish_mock.call_args_list[-1].kwargs.get("title"),
            "existing title"
        )


if __name__ == "__main__":
    unittest.main()
