from testing import cptestcase
from testing import helpers
from testing import assertions
from types import SimpleNamespace
import cherrypy
import apps.homepage.main
import unittest
import mock

class TestHomepage(cptestcase.BaseCherryPyTestCase, assertions.ResponseAssertions):
    @classmethod
    def setUpClass(cls):
        helpers.start_server(apps.homepage.main.Controller)

    @classmethod
    def tearDownClass(cls):
        helpers.stop_server()

    def test_allow(self):
        response = self.request("/", method="HEAD")
        self.assertAllowedMethods(response, ("GET",))

    def test_returnsHtml(self):
        """GET returns text/html by default"""

        response = self.request("/")
        self.assertHtml(response, "class=\"module")

    def test_refusesJson(self):
        """This endpoint does not support JSON responses"""

        response = self.request("/", as_json=True)
        self.assertEqual(response.code, 406)
        self.assertEqual(response.body, '')

    def test_refusesText(self):
        """This endpoint does not support text responses"""

        response = self.request("/", as_text=True)
        self.assertEqual(response.code, 406)
        self.assertEqual(response.body, '')

    def test_emptyAppList(self):
        """The empty-app cast is handled gracefully"""

        controller = apps.homepage.main.Controller()

        app_fixture = {}

        result = controller.catalog_apps(app_fixture)

        self.assertEqual(result, [])

    def test_appWithoutDocstring(self):
        """An app controller with no docstring is handled gracefully"""

        target = apps.homepage.main.Controller()

        fake_controller = SimpleNamespace(root=None)

        result = target.catalog_apps({"/fake_app": fake_controller})

        self.assertEqual(len(result), 1)
