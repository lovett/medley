"""
Test suite for the topics app.
"""

import unittest
import mock
from testing.assertions import ResponseAssertions
from testing import helpers
from testing.cptestcase import BaseCherryPyTestCase
import apps.topics.main


class TestTopics(BaseCherryPyTestCase, ResponseAssertions):
    """
    Tests for the topics application controller
    """

    @classmethod
    def setUpClass(cls):
        """Start a faux cherrypy server."""
        helpers.start_server(apps.topics.main.Controller)

    @classmethod
    def tearDownClass(cls):
        """Shut down the faux server."""
        helpers.stop_server()

    @classmethod
    def setUp(cls):
        """Define fixtures."""

        cls.html_fixture = """<html>
        <ul id="crs_pane">
          <li>
            <a id="crs_itemLink1" href="http://example.com/?q=link1">link1</a>
          </li>
          <li>
            <a id="crs_itemLink2" href="http://example.com/?q=link2">link2</a>
          </li>
          <li>
            <a id="crs_itemLink3" href="http://example.com/?q=link3">link3</a>
          </li>
          <li>
            <a id="crs_itemLink4" href="http://example.com/?q=link3">link4</a>
          </li>
        </ul>
        </html>"""

    def default_side_effect_callback(self, *args, **_):
        """Standard side effect callback returning the html fixture."""

        if args[0] in ("cache:get", "urlfetch:get"):
            return [self.html_fixture]
        return mock.DEFAULT

    def test_allow(self):
        """Verify the controller's supported HTTP methods"""

        response = self.request("/", method="HEAD")
        self.assertAllowedMethods(response, ("GET",))

    def test_sanitizes_count(self):
        """Non-numeric values for count parameter are rejected"""
        response = self.request("/", count="test")
        self.assertEqual(response.code, 400)

    @mock.patch("cherrypy.tools.negotiable._renderHtml")
    @mock.patch("cherrypy.engine.publish")
    def test_repeat_list_until_count(self, publish_mock, render_mock):
        """The number of links is padded to the count parameter"""

        publish_mock.side_effect = self.default_side_effect_callback

        target_count = 13

        self.request("/", count=target_count)

        self.assertEqual(
            len(helpers.html_var(render_mock, "topics")),
            target_count
        )

    @mock.patch("cherrypy.tools.negotiable._renderHtml")
    @mock.patch("cherrypy.engine.publish")
    def test_trim_list_to_count(self, publish_mock, render_mock):
        """The number of links returned is reduced to match the count
        parameter"""

        publish_mock.side_effect = self.default_side_effect_callback

        target_count = 2

        self.request("/", count=target_count)

        self.assertEqual(
            len(helpers.html_var(render_mock, "topics")),
            target_count
        )

    @mock.patch("cherrypy.engine.publish")
    def test_cache_miss_triggers_fetch(self, publish_mock):
        """A urlfetch occurs when a cached value is not present"""

        def side_effect(*args, **_):
            """Side effects local function"""
            if args[0] == "cache:get":
                return [None]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        self.request("/", count=8)

        publish_calls = [args[0][0] for args in publish_mock.call_args_list]

        self.assertTrue("urlfetch:get" in publish_calls)
        self.assertTrue("cache:set" in publish_calls)

    @mock.patch("cherrypy.engine.publish")
    def test_fetch_failure(self, publish_mock):
        """An error is returned if the url fetch fails."""

        def side_effect(*args, **_):
            """Side effects local function"""
            if args[0] in ("cache:get", "urlfetch:get"):
                return [None]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        response = self.request("/")

        self.assertEqual(response.code, 503)

    @mock.patch("cherrypy.engine.publish")
    def test_expires_header(self, publish_mock):
        """The response sends an expires header

        By testing against the JSON repsonse, there aren't any complications
        with the publish mock and the HTML template lookup.
        """

        publish_mock.side_effect = self.default_side_effect_callback

        response = self.request("/", count=8, as_json=True)
        self.assertTrue("GMT" in response.headers.get("Expires"))


if __name__ == "__main__":
    unittest.main()
