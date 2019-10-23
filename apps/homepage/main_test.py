"""
Test suite for the homepage app
"""

import unittest
from types import SimpleNamespace
import mock
from testing.assertions import ResponseAssertions
from testing import helpers
from testing.cptestcase import BaseCherryPyTestCase
import apps.homepage.main


class TestHomepage(BaseCherryPyTestCase, ResponseAssertions):
    """
    Tests for the homepage application controller
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
        if args[0] == "memorize:check_etag":
            return [False]

        return mock.DEFAULT

    def test_allow(self):
        """Verify the controller's supported HTTP methods"""
        response = self.request("/", method="HEAD")
        self.assert_allowed(response, ("GET",))

    def test_exposed(self):
        """The application is publicly available."""
        self.assert_exposed(apps.homepage.main.Controller)

    def test_user_facing(self):
        """The application is displayed in the homepage app."""
        self.assert_user_facing(apps.homepage.main.Controller)

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

        response = self.request("/", as_json=True)
        self.assertEqual(response.code, 406)
        self.assertEqual(response.body, '')

    @mock.patch("cherrypy.engine.publish")
    def test_refuses_text(self, publish_mock):
        """This endpoint does not support text responses"""

        publish_mock.side_effect = self.default_side_effect_callback

        response = self.request("/", as_text=True)
        self.assertEqual(response.code, 406)
        self.assertEqual(response.body, '')

    def test_empty_app_list(self):
        """The empty-app cast is handled gracefully"""

        controller = apps.homepage.main.Controller()

        app_fixture = {}

        result = controller.catalog_apps(app_fixture)

        self.assertEqual(result, [])

    def test_app_without_docstring(self):
        """An app controller with no module docstring is handled gracefully"""

        target = apps.homepage.main.Controller()

        fake_controller = SimpleNamespace(root=None)

        result = target.catalog_apps({"/fake_app": fake_controller})

        self.assertEqual(len(result), 1)


if __name__ == "__main__":
    unittest.main()
