import cptestcase
import helpers
import unittest
import apps.topics.main
import mock
import util.db
import time


class TestTopics(cptestcase.BaseCherryPyTestCase):
    @classmethod
    def setUpClass(cls):
        helpers.start_server(apps.topics.main.Controller)

    @classmethod
    def tearDownClass(cls):
        helpers.stop_server()

    @mock.patch("util.db.cacheGet")
    def test_returnsHtml(self, cacheGetMock):
        """It returns HTML"""
        cacheGetMock.return_value = ("<html></html>", time.time())
        response = self.request("/")
        self.assertEqual(response.code, 200)
        self.assertTrue(helpers.response_is_html(response))
        self.assertTrue("<main" in response.body)
        self.assertTrue(cacheGetMock.called)

if __name__ == "__main__":
    unittest.main()
