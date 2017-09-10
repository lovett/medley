from testing import assertions
from testing import cptestcase
from testing import helpers
import apps.later.main
import cherrypy
import mock
import unittest

class TestLater(cptestcase.BaseCherryPyTestCase, assertions.ResponseAssertions):

    @classmethod
    def setUpClass(cls):
        helpers.start_server(apps.later.main.Controller)

    @classmethod
    def tearDownClass(cls):
        helpers.stop_server()

    def test_allow(self):
        response = self.request("/", method="HEAD")
        self.assertAllowedMethods(response, ("GET",))

    def test_returnsHtml(self):
        """A GET request returns a form for adding a bookmark"""
        response = self.request("/")
        self.assertEqual(response.code, 200)

    def test_bookmarkletUrlProtocol(self):
        """If running under HTTPS, the bookmarklet url uses HTTPS"""

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

    @mock.patch("cherrypy.tools.negotiable._renderHtml")
    @mock.patch("cherrypy.engine.publish")
    def test_urlLookup(self, publishMock, renderMock):
        """An existing bookmark is fetched by url, overwriting querystring values"""

        def side_effect(*args, **kwargs):
            if (args[0] == "archive:find"):
                return [{
                    "title": "existing title",
                    "tags": None,
                    "comments": None
                }]

        publishMock.side_effect = side_effect

        self.request("/", url="http://example.com", title="my title")

        template_vars = renderMock.call_args[0][0]["html"][1]

        self.assertEqual("existing title", template_vars["title"])
        self.assertTrue("already been bookmarked" in template_vars["error"])


if __name__ == "__main__":
    unittest.main()
