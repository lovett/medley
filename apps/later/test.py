import cherrypy
import cptestcase
import helpers
import unittest
import responses
import apps.later.main
import apps.archive.models
import mock
import tempfile
import shutil

class TestLater(cptestcase.BaseCherryPyTestCase):

    temp_dir = None

    @classmethod
    def setUpClass(cls):
        helpers.start_server(apps.later.main.Controller)
        cherrypy.config["timezone"] = "America/New_York"

    @classmethod
    def tearDownClass(cls):
        helpers.stop_server()

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="archive-test")
        cherrypy.config["database_dir"] = self.temp_dir

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_returnsHtml(self):
        """A GET request returns a form for adding a bookmark"""
        response = self.request("/")
        self.assertEqual(response.code, 200)

    def test_bookmarkletUrlProtocol(self):
        """If application is running under HTTPS, the bookmarklet url use HTTPS"""
        host = "bookmark.hostname.example.com"
        response = self.request("/", headers={
            "Host": host,
            "X-HTTPS": "On"
        })
        self.assertEqual(response.code, 200)
        self.assertTrue("https://{}".format(host) in response.body)


    def test_populatesTitle(self):
        """The title field is prepopulated if provided via querystring"""
        samples = (
            ("It's a <i>sample</i> title", "It&#39;s a sample title")
        )

        for sample in samples:
            response = self.request("/", title=sample[0])
            self.assertTrue(sample[1] in response.body)

    def test_populatesTags(self):
        """The tags field is prepopulated if provided via querystring"""
        samples = (
            ("<b>tag1</b>, tag2", "tag1, tag2")
        )

        for sample in samples:
            response = self.request("/", tags=sample[0])
            self.assertTrue(sample[1] in response.body)

    def test_populatesComments(self):
        """The comments field is prepopulated if provided via querystring"""
        samples = (
            ("<b>comment</b>", "comment."),
            ("Sentence 1. Sentence 2.", "Sentence 1. Sentence 2"),
            ("Word 1            word 2", "Word 1 word 2"),
            ("trailing whitespace        ", "trailing whitespace.")
        )

        for sample in samples:
            response = self.request("/", comments=sample[0])
            self.assertTrue(sample[1] in response.body)

    @mock.patch("apps.archive.models.Archive.find")
    def test_urlLookup(self, findMock):
        """An existing bookmark is fetched by url, overwriting querystring values"""
        findMock.return_value = {
            "title": "existing title",
            "tags": None,
            "comments": None
        }
        response = self.request("/", url="http://example.com", title="my title")
        self.assertTrue(findMock.called)
        self.assertTrue("existing title" in response.body)
        self.assertFalse("my title" in response.body)
        self.assertTrue("already been bookmarked" in response.body)


if __name__ == "__main__":
    unittest.main()
