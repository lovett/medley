import cherrypy
import cptestcase
import helpers
import unittest
import responses
import apps.captures.main
import apps.captures.models
import mock
import tempfile
import shutil

class TestTopics(cptestcase.BaseCherryPyTestCase):
    @classmethod
    def setUpClass(cls):
        helpers.start_server(apps.captures.main.Controller)

    @classmethod
    def tearDownClass(cls):
        helpers.stop_server()

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="archive-test")
        cherrypy.config["database_dir"] = self.temp_dir


    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_returnsHtml(self):
        """It returns HTML"""
        response = self.request("/")
        self.assertEqual(response.code, 200)
        self.assertTrue(helpers.response_is_html(response))

    @mock.patch("apps.captures.models.CaptureManager.recent")
    @mock.patch("apps.captures.models.CaptureManager.search")
    def test_performsSearch(self, searchMock, recentMock):
        """Recent captures are returned by default"""
        searchMock.return_value = []
        recentMock.return_value = []
        response = self.request("/")
        self.assertTrue(recentMock.called)
        self.assertFalse(searchMock.called)

    @mock.patch("apps.captures.models.CaptureManager.recent")
    @mock.patch("apps.captures.models.CaptureManager.search")
    def test_performsSearch(self, searchMock, recentMock):
        """Recent captures are returned by default"""
        searchMock.return_value = []
        recentMock.return_value = []
        response = self.request("/", q="test")
        self.assertFalse(recentMock.called)
        self.assertTrue(searchMock.called)


if __name__ == "__main__":
    unittest.main()
