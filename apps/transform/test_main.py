from testing import cptestcase
from testing import helpers
import unittest
import apps.transform.main


class TestTransform(cptestcase.BaseCherryPyTestCase):
    @classmethod
    def setUpClass(cls):
        helpers.start_server(apps.transform.main.Controller)

    @classmethod
    def tearDownClass(cls):
        helpers.stop_server()

    def test_returnsHtml(self):
        """HTML is returned by default"""
        response = self.request("/")
        self.assertEqual(response.code, 200)
        self.assertTrue(helpers.response_is_html(response))
        self.assertTrue("<form" in response.body)

    def test_lowercaseHtml(self):
        """Input is converted to lowercase and returned as HTML"""
        response = self.request(path="/",
                                method="POST",
                                transform="lower",
                                value="TEST")
        self.assertTrue(helpers.response_is_html(response))
        self.assertTrue("""<div id="result">test</div>""" in response.body)

    def test_lowercaseJson(self):
        """Input is converted to lowercase and returned as JSON"""
        response = self.request(path="/",
                                method="POST",
                                as_json=True,
                                transform="lower",
                                value="TEST")
        self.assertTrue(helpers.response_is_json(response))
        self.assertEqual(response.body["result"], "test")

    def test_lowercaseText(self):
        """Input is coverted to lowercase and returned as plain text"""
        response = self.request(path="/",
                                method="POST",
                                as_plain=True,
                                transform="lower",
                                value="TEST")
        self.assertTrue(helpers.response_is_text(response))
        self.assertEqual(response.body, "test")

    def test_uppercase(self):
        """Input is converted to uppercase"""
        response = self.request(path="/",
                                method="POST",
                                as_plain=True,
                                transform="upper",
                                value="test")
        self.assertEqual(response.body, "TEST")

    def test_urlencode(self):
        """Input is url-encoded"""
        response = self.request(path="/",
                                method="POST",
                                as_plain=True,
                                transform="urlencode",
                                value="this is a test")
        self.assertEqual(response.body, "this+is+a+test")

    def test_urldecode(self):
        """Input is url-encoded"""
        response = self.request(path="/",
                                method="POST",
                                as_plain=True,
                                transform="urldecode",
                                value="this+is+a+test")
        self.assertEqual(response.body, "this is a test")

    def test_capitalize(self):
        """Input is capitalized"""
        response = self.request(path="/",
                                method="POST",
                                as_plain=True,
                                transform="capitalize",
                                value="test Case")
        self.assertEqual(response.body, "Test case")

    def test_title(self):
        """Input is converted to titlecase"""
        response = self.request(path="/",
                                method="POST",
                                as_plain=True,
                                transform="title",
                                value="this iS a TEst 1999")
        self.assertEqual(response.body, "This Is A Test 1999")

    def test_invalidTransform(self):
        """Unrecognized values for the transform parameter return leave the value unmodified"""
        val = "test"
        response = self.request(
            path="/",
            method="POST",
            as_plain=True,
            transform="example",
            value=val
        )
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body, val)

    def test_paramsOptional(self):
        """Transform and value parameters are optional"""
        response = self.request(path="/",
                               method="POST",
                               as_plain=True)
        self.assertEqual(response.code, 200)



if __name__ == "__main__":
    unittest.main()
