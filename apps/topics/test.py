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

    @mock.patch("util.net.getUrl")
    @mock.patch("util.db.cacheSet")
    @mock.patch("util.db.cacheGet")
    def test_requestsUrl(self, cacheGetMock, cacheSetMock, getUrlMock):
        """It requests a URL if the cache is empty"""
        cacheGetMock.return_value = None
        cacheSetMock.return_value = None
        getUrlMock.return_value = "<html></html>"

        response = self.request("/")
        self.assertTrue(getUrlMock.called)
        self.assertTrue(cacheSetMock.called)

    @mock.patch("util.net.getUrl")
    @mock.patch("util.db.cacheSet")
    @mock.patch("util.db.cacheGet")
    def test_extractsLinks(self, cacheGetMock, cacheSetMock, getUrlMock):
        """It extracts links from the requested URL and handles escaping"""
        cacheGetMock.return_value = None
        cacheSetMock.return_value = None
        getUrlMock.return_value = """
        <html>
        <ul id="crs_pane">
            <li><a href="http://example.com/?q=link1">link1</a></li>
            <li><a href="http://example.com/?q=link2+multiword">link2 multiword</a></li>
            <li><a href="http://example.com/?q=link3%20multiword">link3 multiword</a></li>
            <li><a href="http://example.com/?q=%23link4">link4 hashtag</a></li>
            <li><a href="http://example.com/link5">link5</a></li>
        </ul>
        </html>"""

        response = self.request("/")
        self.assertTrue(getUrlMock.called)

        # single word query
        self.assertTrue("?q=link1" in response.body)
        self.assertTrue(">link1</a>" in response.body)

        # multiword escaped query
        self.assertTrue("?q=link2%20multiword" in response.body)
        self.assertTrue(">link2 multiword</a>" in response.body)
        self.assertTrue("?q=link3%20multiword" in response.body)
        self.assertTrue(">link3 multiword</a>" in response.body)

        # hashtag query
        self.assertTrue("?q=%23link4" in response.body)
        self.assertTrue(">#link4</a>" in response.body)

        # non-query link
        self.assertFalse("?q=link5" in response.body)


if __name__ == "__main__":
    unittest.main()
