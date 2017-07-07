from testing import cptestcase
from testing import helpers
import apps.headers.main
import unittest


class TestHeaders(cptestcase.BaseCherryPyTestCase):
    @classmethod
    def setUpClass(cls):
        helpers.start_server(apps.headers.main.Controller)

    @classmethod
    def tearDownClass(cls):
        helpers.stop_server()

    def test_returnsHtml(self):
        """It returns HTML by default"""
        response = self.request("/")
        self.assertEqual(response.code, 200)
        self.assertTrue(helpers.response_is_html(response))
        self.assertTrue("<table" in response.body)

    def test_returnsJson(self):
        """It returns JSON if requested"""
        response = self.request("/", as_json=True)
        self.assertEqual(response.code, 200)
        self.assertTrue(helpers.response_is_json(response))
        header, value = next(pair for pair in response.body if pair[0] == "Accept")
        self.assertTrue(helpers.response_is_json(response))

    def test_returnsText(self):
        """It returns plain text if requested"""
        response = self.request("/", as_plain=True)
        self.assertEqual(response.code, 200)
        self.assertTrue(helpers.response_is_text(response))
        self.assertTrue("Accept" in response.body)

    def test_noVars(self):
        """It takes no querystring arguments"""
        response = self.request("/?this=that")
        self.assertEqual(response.code, 404)

    def test_noParams(self):
        """It takes no route parameters"""
        response = self.request("/test")
        self.assertEqual(response.code, 404)

    def test_customHeader(self):
        """It recognizes custom headers"""
        response = self.request("/", headers={"Special_Header": "Special Value"}, as_json=True)
        header, value = next(pair for pair in response.body if pair[0] == "Special_Header")
        self.assertEqual(value, "Special Value")
