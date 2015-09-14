import cptestcase
import helpers
import unittest
import apps.lettercase.main

def setup_module():
    helpers.start_server(apps.lettercase.main.Controller)

def teardown_module():
    helpers.stop_server()

class TestLettercase(cptestcase.BaseCherryPyTestCase):
    def test_returnsHtml(self):
        """It returns HTML by default"""
        response = self.request("/")
        self.assertEqual(response.code, 200)
        self.assertTrue(helpers.response_is_html(response))
        self.assertTrue("<form" in response.body)

    def test_lowercaseHtml(self):
        """It converts input to lowercase and returns HTML"""
        response = self.request(path="/",
                                method="POST",
                                style="lower",
                                value="TEST")
        self.assertTrue(helpers.response_is_html(response))
        self.assertTrue("""<div id="result">test</div>""" in response.body)

    def test_lowercaseJson(self):
        """It converts input to lowercase and returns JSON"""
        response = self.request(path="/",
                                method="POST",
                                as_json=True,
                                style="lower",
                                value="TEST")
        self.assertTrue(helpers.response_is_json(response))
        self.assertEqual(response.body["result"], "test")

    def test_lowercaseText(self):
        """It converts input to lowercase and returns plain  text"""
        response = self.request(path="/",
                                method="POST",
                                as_plain=True,
                                style="lower",
                                value="TEST")
        self.assertTrue(helpers.response_is_text(response))
        self.assertEqual(response.body, "test")

    def test_uppercase(self):
        """It converts input to uppercase"""
        response = self.request(path="/",
                                method="POST",
                                as_plain=True,
                                style="upper",
                                value="test")
        self.assertEqual(response.body, "TEST")

    def test_title(self):
        """It converts its input to title case """
        response = self.request(path="/",
                                method="POST",
                                as_plain=True,
                                style="title",
                                value="this iS a TEst 1999")
        self.assertEqual(response.body, "This Is A Test 1999")



if __name__ == "__main__":
    unittest.main()
