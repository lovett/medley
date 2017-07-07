from testing import cptestcase
from testing import helpers
import unittest
import apps.bounce.main


class TestBounce(cptestcase.BaseCherryPyTestCase):
    @classmethod
    def setUpClass(cls):
        helpers.start_server(apps.bounce.main.Controller)

    @classmethod
    def tearDownClass(cls):
        helpers.stop_server()

    def test_returnsHtml(self):
        """It returns HTML by default"""
        response = self.request("/")
        self.assertEqual(response.code, 200)
        self.assertTrue(helpers.response_is_html(response))

if __name__ == "__main__":
    unittest.main()
