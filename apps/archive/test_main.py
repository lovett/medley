from testing import cptestcase
from testing import helpers
import cherrypy
import responses
import apps.archive.main
import apps.archive.models
import mock
import time
import tempfile
import shutil
import util.sqlite_converters

class TestArchive(cptestcase.BaseCherryPyTestCase):

    temp_dir = None

    @classmethod
    def setUpClass(cls):
        helpers.start_server(apps.archive.main.Controller)
        cherrypy.config["timezone"] = "America/New_York"

    @classmethod
    def tearDownClass(cls):
        helpers.stop_server()

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="archive-test")
        cherrypy.config["database_dir"] = self.temp_dir

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    @mock.patch("apps.archive.models.Archive.search")
    @mock.patch("apps.archive.models.Archive.recent")
    def test_noRecentBookmarks(self, recentMock, searchMock):
        """If the database is empty, a no-records message is returned"""
        recentMock.return_value = []
        response = self.request("/")
        self.assertEqual(response.code, 200)
        self.assertTrue(recentMock.called)
        self.assertTrue("Nothing found" in response.body)
        self.assertFalse(searchMock.called)

    @mock.patch("apps.archive.models.Archive.search")
    @mock.patch("apps.archive.models.Archive.recent")
    def test_recentBookmarks(self, recentMock, searchMock):
        """Recently bookmarked URLs are grouped by date"""
        template = {
            "url": "http://example.com",
            "domain": "example.com"
        }

        # Four bookmarks created on three days, to demonstrate grouping
        recentMock.return_value = [
            dict({"created": util.sqlite_converters.convert_date(b"2015-01-03 01:00:00")}, **template),
            dict({"created": util.sqlite_converters.convert_date(b"2015-01-03 01:01:00")}, **template),
            dict({"created": util.sqlite_converters.convert_date(b"2015-01-02 01:00:00")}, **template),
            dict({"created": util.sqlite_converters.convert_date(b"2015-01-01 01:00:00")}, **template),
        ]


        response = self.request("/")
        self.assertEqual(response.code, 200)
        self.assertTrue(recentMock.called)
        self.assertTrue("Jan 02, 2015</h1>" in response.body)
        self.assertTrue("Jan 01, 2015</h1>" in response.body)
        self.assertTrue("Dec 31, 2014</h1>" in response.body)
        self.assertFalse(searchMock.called)

    @mock.patch("apps.archive.models.Archive.search")
    @mock.patch("apps.archive.models.Archive.recent")
    def test_searchBookmarks(self, recentMock, searchMock):
        """Searching for bookmarks bypasses recent bookmarks"""
        searchMock.return_value = []
        response = self.request("/", q="test")
        self.assertEqual(response.code, 200)
        self.assertFalse(recentMock.called)
        self.assertTrue(searchMock.called)

    @mock.patch("apps.archive.models.Archive.reduceHtmlTitle")
    @mock.patch("util.net.getHtmlTitle")
    @mock.patch("apps.archive.models.Archive.addFullText")
    @mock.patch("apps.archive.models.Archive.add")
    @mock.patch("apps.archive.models.Archive.fetch")
    @mock.patch("apps.archive.models.Archive.find")
    def test_addBookmarkSuccess(self, findMock, fetchMock, addMock, addFullTextMock, getHtmlTitleMock, reduceHtmlTitleMock):
        """A bookmark can be added to the database"""
        findMock.return_value = None
        fetchMock.return_value = "<html>test</html>"
        addMock.return_value = 1
        addFullTextMock.return_value = True
        getHtmlTitleMock.return_value = "test"
        reduceHtmlTitleMock.return_value = "test"

        response = self.request("/", url="http://example.com", method="POST")
        self.assertEqual(response.code, 204)
        self.assertTrue(addMock.called)
        self.assertTrue(findMock.called)
        self.assertTrue(getHtmlTitleMock.called)
        self.assertTrue(reduceHtmlTitleMock.called)

    @mock.patch("apps.archive.models.Archive.addFullText")
    @mock.patch("apps.archive.models.Archive.add")
    @mock.patch("apps.archive.models.Archive.fetch")
    @mock.patch("apps.archive.models.Archive.find")
    def test_updateBookmarkSuccess(self, findMock, fetchMock, addMock, addFullTextMock):
        """A previously added bookmark can be updated"""
        findMock.return_value = True
        addMock.return_value = 1
        addFullTextMock.return_value = True

        response = self.request("/", title="new title", url="http://example.com", method="POST")

        self.assertEqual(response.code, 204)
        self.assertFalse(fetchMock.called)
        self.assertTrue(addMock.called)
        self.assertTrue(findMock.called)



    @mock.patch("apps.archive.models.Archive.remove")
    def test_deleteRequiresId(self, removeMock):
        """Deletion is refused if the bookmark id is not found"""
        response = self.request("/", uid=123456789, method="DELETE")
        self.assertEqual(response.code, 404)
        self.assertFalse(removeMock.called)

    def test_deleteBookmark(self):
        """An existing bookmark can be deleted"""
        archive = apps.archive.models.Archive()
        url_id = archive.add("http://example.com", "Test")
        response = self.request("/", uid=url_id, method="DELETE")
        self.assertEqual(response.code, 200)

if __name__ == "__main__":
    unittest.main()
