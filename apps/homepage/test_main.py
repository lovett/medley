"""
Test suite for the homepage app
"""

import unittest
from types import SimpleNamespace
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

    def test_allow(self):
        """Verify the controller's supported HTTP methods"""
        response = self.request("/", method="HEAD")
        self.assertAllowedMethods(response, ("GET",))

    def test_returns_html(self):
        """GET returns text/html by default"""

        response = self.request("/")
        self.assertHtml(response, "class=\"module")

    def test_refuses_json(self):
        """This endpoint does not support JSON responses"""

        response = self.request("/", as_json=True)
        self.assertEqual(response.code, 406)
        self.assertEqual(response.body, '')

    def test_refuses_text(self):
        """This endpoint does not support text responses"""

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
        """An app controller with no docstring is handled gracefully"""

        target = apps.homepage.main.Controller()

        fake_controller = SimpleNamespace(root=None)

        result = target.catalog_apps({"/fake_app": fake_controller})

        self.assertEqual(len(result), 1)


if __name__ == "__main__":
    unittest.main()
