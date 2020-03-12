"""
Test suite for the homepage app
"""

import types
import unittest
import mock
from testing.assertions import ResponseAssertions
from testing import helpers
from testing.cptestcase import BaseCherryPyTestCase
import apps.homepage.main


class TestHomepage(BaseCherryPyTestCase, ResponseAssertions):
    """
    Tests for the application controller.
    """

    @classmethod
    def setUpClass(cls):
        helpers.start_server(apps.homepage.main.Controller)

    @classmethod
    def tearDownClass(cls):
        helpers.stop_server()

    @staticmethod
    def default_side_effect_callback(*args, **_):
        """
        The standard mock side effect function used by all tests
        """
        if args[0] == "memorize:get":
            return [(False, None)]

        if args[0] == "jinja:render":
            return [""]

        return mock.DEFAULT

    def test_allow(self):
        """Verify the controller's supported HTTP methods"""
        response = self.request("/", method="HEAD")
        self.assert_allowed(response, ("GET",))

    def test_exposed(self):
        """The application is publicly available."""
        self.assert_exposed(apps.homepage.main.Controller)

    def test_not_show_on_homepage(self):
        """The application is not displayed in the homepage app."""
        self.assert_not_show_on_homepage(apps.homepage.main.Controller)

    @mock.patch("cherrypy.engine.publish")
    def test_returns_html(self, publish_mock):
        """GET returns text/html by default"""
        publish_mock.side_effect = self.default_side_effect_callback

        response = self.request("/")
        self.assertEqual(response.code, 200)
        self.assert_html(response)

    @mock.patch("cherrypy.engine.publish")
    def test_refuses_json(self, publish_mock):
        """This endpoint does not support JSON responses"""

        publish_mock.side_effect = self.default_side_effect_callback

        response = self.request("/", accept="json")
        self.assertEqual(response.code, 406)

    @mock.patch("cherrypy.engine.publish")
    def test_returns_org(self, publish_mock):
        """GET supports text/x-org output."""

        def side_effect(*args, **_):
            """Side effects local function"""
            if args[0] == "memorize:get":
                return [(True, "abc123")]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        response = self.request("/", accept="org")
        self.assertEqual(response.code, 200)

    @mock.patch("cherrypy.engine.publish")
    def test_all_apps(self, publish_mock):
        """If the first URL path segment is "all", the output includes all
        apps, not just the ones meant for display on the homepage."""

        def side_effect(*args, **_):
            """Side effects local function"""
            if args[0] == "memorize:get":
                return [(True, "abc123")]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        response = self.request("/all", accept="org")
        self.assertIn("homepage", response.body)

    @mock.patch("cherrypy.engine.publish")
    def test_valid_etag(self, publish_mock):
        """A valid etag produces a 304 response."""

        def side_effect(*args, **_):
            """Side effects local function"""
            if args[0] == "memorize:get":
                return [(True, "abc123")]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        response = self.request("/", headers={"If-None-Match": "abc123"})
        self.assertEqual(response.code, 304)
        self.assertEqual(response.body, "")

    @mock.patch("cherrypy.engine.publish")
    def test_invalid_etag(self, publish_mock):
        """An invalid etag produces a 200 response."""

        def side_effect(*args, **_):
            """Side effects local function"""
            if args[0] == "memorize:get":
                return [(True, "abc456")]
            if args[0] == "jinja:render":
                return [""]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        response = self.request("/", headers={"If-None-Match": "example"})
        self.assertEqual(response.code, 200)

    @mock.patch("cherrypy.engine.publish")
    def test_refuses_text(self, publish_mock):
        """This endpoint does not support text responses"""

        publish_mock.side_effect = self.default_side_effect_callback

        response = self.request("/", accept="text")
        self.assertEqual(response.code, 406)

    def test_app_without_docstring(self):
        """An app controller with no module docstring is handled gracefully."""

        target = apps.homepage.main.Controller()

        fake_controller = types.new_class("fake")

        result = target.catalog_apps({"/fake_app": fake_controller})

        self.assertEqual(len(result), 1)


if __name__ == "__main__":
    unittest.main()
