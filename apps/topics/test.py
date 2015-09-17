import cptestcase
import helpers
import unittest
import apps.topics.main
import mock
import util.db
import time

def setup_module():
    helpers.start_server(apps.topics.main.Controller)

def teardown_module():
    helpers.stop_server()

class TestTopics(cptestcase.BaseCherryPyTestCase):

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
