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

    @mock.patch("cherrypy.tools.negotiable._renderHtml")
    @mock.patch("cherrypy.engine.publish")
    def test_populatesTags(self, publishMock, renderMock):
        """The tags field is prepopulated if provided via querystring"""

        def side_effect(*args, **kwargs):
            if args[0].startswith("markup:"):
                return ["abc123"]

        publishMock.side_effect = side_effect

        response = self.request("/", tags="hello")
        template_vars = renderMock.call_args[0][0]["html"][1]

        self.assertEqual(template_vars["tags"], "abc123")

    @mock.patch("cherrypy.tools.negotiable._renderHtml")
    @mock.patch("cherrypy.engine.publish")
    def test_populatesComments(self, publishMock, renderMock):
        """The comments field is prepopulated if provided via querystring

        A period is also added to make the populated value a sentence.
        """
        def side_effect(*args, **kwargs):
            if args[0].startswith("markup:"):
                return ["abc456"]

        publishMock.side_effect = side_effect

        response = self.request("/", comments="hello")
        template_vars = renderMock.call_args[0][0]["html"][1]

        self.assertEqual(template_vars["comments"], "abc456.")


    @mock.patch("cherrypy.tools.negotiable._renderHtml")
    @mock.patch("cherrypy.engine.publish")
    def test_urlLookup(self, publishMock, renderMock):
        """An existing bookmark is fetched by url, overwriting querystring values"""

        def side_effect(*args, **kwargs):
            if args[0].startswith("markup:"):
                return [args[1]]
            if args[0] == "archive:find":
                return [{
                    "title": "existing title",
                    "tags": None,
                    "comments": None
                }]

        publishMock.side_effect = side_effect

        response = self.request("/", url="http://example.com", title="my title")

        template_vars = renderMock.call_args[0][0]["html"][1]

        self.assertEqual("existing title", template_vars["title"])
        self.assertTrue("already been bookmarked" in template_vars["error"])


if __name__ == "__main__":
    unittest.main()
