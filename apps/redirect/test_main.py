from testing import assertions
from testing import cptestcase
from testing import helpers
import apps.redirect.main
import cherrypy
import datetime
import mock
import unittest

class TestTemplate(cptestcase.BaseCherryPyTestCase, assertions.ResponseAssertions):
    """Unit tests for the redirect app"""

    @classmethod
    def setUpClass(cls):
        helpers.start_server(apps.redirect.main.Controller)

    @classmethod
    def tearDownClass(cls):
        helpers.stop_server()

    def extract_template_vars(self, mock):
        return mock.call_args[0][0]["html"][1]

    def test_allow(self):
        response = self.request("/", method="HEAD")
        self.assertAllowedMethods(response, ("GET",))

    @mock.patch("cherrypy.tools.negotiable._renderHtml")
    def test_noDestination(self, renderMock):
        response = self.request("/")

        template_vars = self.extract_template_vars(renderMock)

        self.assertEqual(template_vars["app_name"], apps.redirect.main.Controller.name)
        self.assertEqual(template_vars["dest"], None)

    @mock.patch("cherrypy.tools.negotiable._renderHtml")
    def test_encodedDestination(self, renderMock):
        response = self.request("/", u="http%3A%2F%2Fexample.com")

        template_vars = self.extract_template_vars(renderMock)

        self.assertEqual(template_vars["app_name"], apps.redirect.main.Controller.name)
        self.assertEqual(template_vars["dest"], "http://example.com")

    @mock.patch("cherrypy.tools.negotiable._renderHtml")
    def test_unencodedDestination(self, renderMock):
        response = self.request("/", u="http://example.net")

        template_vars = self.extract_template_vars(renderMock)

        self.assertEqual(template_vars["app_name"], apps.redirect.main.Controller.name)
        self.assertEqual(template_vars["dest"], "http://example.net")

    @mock.patch("cherrypy.tools.negotiable._renderHtml")
    def test_destinationWithEncodedQuerystring(self, renderMock):
        response = self.request("/", u="http%3A%2F%2Fexample.com%3Fhello%3Dworld")

        template_vars = self.extract_template_vars(renderMock)

        self.assertEqual(template_vars["app_name"], apps.redirect.main.Controller.name)
        self.assertEqual(template_vars["dest"], "http://example.com?hello=world")


if __name__ == "__main__":
    unittest.main()
