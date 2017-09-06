from testing import cptestcase
from testing import helpers
import unittest
import apps.topics.main
import mock

class TestTopics(cptestcase.BaseCherryPyTestCase):

    @classmethod
    def setUpClass(cls):
        helpers.start_server(apps.topics.main.Controller)

    @classmethod
    def tearDownClass(cls):
        helpers.stop_server()

    @classmethod
    def setUp(self):

        self.html_fixture = """
        <html>
        <ul id="crs_pane">
            <li><a id="crs_itemLink1" href="http://example.com/?q=link1">link1</a></li>
            <li><a id="crs_itemLink2" href="http://example.com/?q=link2">link2</a></li>
            <li><a id="crs_itemLink3" href="http://example.com/?q=link2">link3</a></li>
            <li><a id="crs_itemLink4" href="http://example.com/?q=link2">link4</a></li>
        </ul>
        </html>"""

    def extract_template_vars(self, mock):
        return mock.call_args[0][0]["html"][1]

    def default_side_effect_callback(self, *args, **kwargs):
        if args[0] == "cache:get":
            return [self.html_fixture]

    def urlfetch_side_effect_callback(self, *args, **kwargs):
        if args[0] == "urlfetch:get":
            return [self.html_fixture]


    def test_sanitizesCount(self):
        """Non-numeric values for count parameter are rejected"""
        response = self.request("/", count="test")
        self.assertEqual(response.code, 400)

    @mock.patch("cherrypy.tools.negotiable._renderHtml")
    @mock.patch("cherrypy.engine.publish")
    def test_repeatListUntilCount(self, publishMock, renderMock):
        """The number of links is padded to the count parameter"""
        publishMock.side_effect = self.default_side_effect_callback

        target_count = 13

        response = self.request("/", count=target_count)

        template_vars = self.extract_template_vars(renderMock)

        self.assertEqual(len(template_vars["topics"]), target_count)

    @mock.patch("cherrypy.tools.negotiable._renderHtml")
    @mock.patch("cherrypy.engine.publish")
    def test_trimListToCount(self, publishMock, renderMock):
        """The number of links returned is reduced to match the count parameter"""
        publishMock.side_effect = self.default_side_effect_callback

        target_count = 2

        response = self.request("/", count=target_count)

        template_vars = self.extract_template_vars(renderMock)

        self.assertEqual(len(template_vars["topics"]), target_count)

    @mock.patch("cherrypy.engine.publish")
    def test_cacheMissTriggersUrlfetch(self, publishMock):
        """A urlfetch occurs when a cached value is not present"""
        publishMock.side_effect = self.urlfetch_side_effect_callback

        response = self.request("/", count=8)

        publish_calls = [args[0][0] for args in publishMock.call_args_list]

        self.assertTrue("urlfetch:get" in publish_calls)
        self.assertTrue("cache:set" in publish_calls)

    @mock.patch("cherrypy.engine.publish")
    def test_fetchFailure(self, publishMock):
        """A urlfetch occurs when a cached value is not present"""

        def side_effect(*args, **kwargs):
            if (args[0] == "urlfetch:get"):
                return [None]

        publishMock.side_effect = side_effect

        response = self.request("/", as_json=True)

        self.assertEqual(response.code, 503)



    @mock.patch("cherrypy.engine.publish")
    def test_expiresHeader(self, publishMock):
        """The response sends an expires header

        By testing against the JSON repsonse, there aren't any complications
        with the publish mock and the HTML template lookup.
        """

        publishMock.side_effect = self.default_side_effect_callback

        response = self.request("/", count=8, as_json=True)
        self.assertTrue("GMT" in response.headers.get("Expires"))

if __name__ == "__main__":
    unittest.main()
