import cptestcase
import helpers
import unittest
import responses
import apps.topics.main
import mock
import util.cache
import time
import shutil
import tempfile
import cherrypy

class TestTopics(cptestcase.BaseCherryPyTestCase):
    temp_dir = None

    @classmethod
    def setUpClass(cls):
        helpers.start_server(apps.topics.main.Controller)

    @classmethod
    def tearDownClass(cls):
        helpers.stop_server()

    @mock.patch("util.cache.Cache.get")
    def test_returnsHtml(self, cacheGetMock):
        """It returns HTML"""
        cacheGetMock.return_value = ("<html></html>", time.time())
        response = self.request("/")
        self.assertEqual(response.code, 200)
        self.assertTrue(helpers.response_is_html(response))
        self.assertTrue("<main" in response.body)
        self.assertTrue("Using cached value" in response.body)
        self.assertTrue(cacheGetMock.called)

    @mock.patch("util.cache.Cache.get")
    def test_numericCount(self, cacheGetMock):
        """It requires a numeric count"""
        response = self.request("/", count="test")
        self.assertEqual(response.code, 400)

        cacheGetMock.return_value = ("<html></html>", time.time())
        response = self.request("/", count="100")
        self.assertEqual(response.code, 200)

    @mock.patch("util.cache.Cache.get")
    def test_limitsTopics(self, cacheGetMock):
        """It requires a numeric count"""
        response = self.request("/", count="test")
        self.assertEqual(response.code, 400)

        cacheGetMock.return_value = ("""
        <html>
            <ul id="crs_pane">
                <li><a href="http://example.com/?q=link1">link1</a></li>
                <li><a href="http://example.com/?q=link2+multiword">link2 multiword</a></li>
                <li><a href="http://example.com/?q=link3%20multiword">link3 multiword</a></li>
                <li><a href="http://example.com/?q=%23link4">link4 hashtag</a></li>
                <li><a href="http://example.com/link5">link5</a></li>
            </ul>
        </html>""", time.time())
        response = self.request("/", count="1")
        self.assertEqual(response.code, 200)
        self.assertTrue("link5" not in response.body)



    @responses.activate
    @mock.patch("util.cache.Cache.set")
    @mock.patch("util.cache.Cache.get")
    def test_requestsUrl(self, cacheGetMock, cacheSetMock):
        """It requests a URL if the cache is empty"""
        cacheGetMock.return_value = None
        cacheSetMock.return_value = None

        response_html = "<html></html>"
        responses.add(responses.GET, "http://www.bing.com/hpm", body=response_html)

        response = self.request("/")
        self.assertEqual(len(responses.calls), 1)
        self.assertTrue(cacheSetMock.called)
        self.assertTrue("The URL was not cached" in response.body)

    @responses.activate
    @mock.patch("util.cache.Cache.set")
    @mock.patch("util.cache.Cache.get")
    def test_extractsLinks(self, cacheGetMock, cacheSetMock):
        """It extracts links from the requested URL and handles escaping"""
        cacheGetMock.return_value = None
        cacheSetMock.return_value = None

        response_html = """
        <html>
        <ul id="crs_pane">
            <li><a href="http://example.com/?q=link1">link1</a></li>
            <li><a href="http://example.com/?q=link2+multiword">link2 multiword</a></li>
            <li><a href="http://example.com/?q=link3%20multiword">link3 multiword</a></li>
            <li><a href="http://example.com/?q=%23link4">link4 hashtag</a></li>
            <li><a href="http://example.com/link5">link5</a></li>
        </ul>
        </html>"""
        responses.add(responses.GET, "http://www.bing.com/hpm", body=response_html)

        response = self.request("/")
        self.assertEqual(len(responses.calls), 1)

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
