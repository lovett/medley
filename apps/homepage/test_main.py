from testing import cptestcase
from testing import helpers
from testing import assertions
import apps.homepage.main
import unittest


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
