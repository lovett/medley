from testing import cptestcase
from testing import helpers
from testing import assertions
import apps.headers.main
import unittest


class TestHeaders(cptestcase.BaseCherryPyTestCase, assertions.ResponseAssertions):
    @classmethod
    def setUpClass(cls):
        helpers.start_server(apps.headers.main.Controller)

    @classmethod
    def tearDownClass(cls):
        helpers.stop_server()

    def test_allow(self):
        response = self.request("/", method="HEAD")
        self.assertAllowedMethods(response, ("GET",))

    def test_returnsHtml(self):
        """GET returns text/html by default"""
        response = self.request("/")
        self.assertHtml(response, "<table")

    def test_returnsJson(self):
        """GET returns application/json if requested"""
        response = self.request("/", as_json=True)
        self.assertEqual(response.code, 200)
        self.assertJson(response)

    def test_returnsText(self):
        """GET returns text/plain if requested"""
        response = self.request("/", as_text=True)
        self.assertEqual(response.code, 200)
        self.assertText(response)

    def test_noquery(self):
        """GET takes no querystring arguments"""
        response = self.request("/?test_noquery=abc123")
        self.assertEqual(response.code, 404)

    def test_customHeader(self):
        """GET recognizes custom headers"""
        response = self.request("/", headers={"Special_Header": "Special Value"}, as_json=True)
        header, value = next(pair for pair in response.body if pair[0] == "Special_Header")
        self.assertEqual(value, "Special Value")
