import cptestcase
import helpers
import unittest
import apps.headers.main

def setup_module():
    helpers.start_server(apps.headers.main.Controller)

def teardown_module():
    helpers.stop_server()

class TestHeaders(cptestcase.BaseCherryPyTestCase):
    def test_returnsHtml(self):
        """It returns HTML by default"""
        response = self.request("/")
        self.assertEqual(response.code, 200)
        self.assertEqual(response.headers["Content-Type"], "text/html;charset=utf-8")
        self.assertTrue("<table" in response.body)

    def test_returnsJson(self):
        """It returns JSON if requested"""
        response = self.request("/", as_json=True)
        self.assertEqual(response.code, 200)
        self.assertEqual(response.headers["Content-Type"], "application/json")
        header, value = next(pair for pair in response.body if pair[0] == "Accept")
        self.assertEqual(value, "application/json")

    def test_returnsPlain(self):
        """It returns plain text if requested"""
        response = self.request("/", as_plain=True)
        self.assertEqual(response.code, 200)
        self.assertEqual(response.headers["Content-Type"], "text/plain;charset=utf-8")
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
        print(response.body)
        header, value = next(pair for pair in response.body if pair[0] == "Special_Header")
        self.assertEqual(value, "Special Value")


if __name__ == "__main__":
    unittest.main()
