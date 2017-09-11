from testing import assertions
from testing import cptestcase
from testing import helpers
import unittest
import apps.bounce.main
import mock

class TestBounce(cptestcase.BaseCherryPyTestCase, assertions.ResponseAssertions):
    @classmethod
    def setUpClass(cls):
        helpers.start_server(apps.bounce.main.Controller)

    @classmethod
    def tearDownClass(cls):
        helpers.stop_server()


    def setUp(self):
        self.controller = apps.bounce.main.Controller()

    def test_allow(self):
        response = self.request("/", method="HEAD")
        self.assertAllowedMethods(response, ("GET", "PUT"))


    def test_siteUrl(self):
        candidates = (
            ("https://example.com/with/a/path", "https://example.com"),
            ("http://example.com/path?and=querystring#andfragment", "http://example.com"),
        )

        for pair in candidates:
            result = self.controller.siteUrl(pair[0])
            self.assertEqual(result, pair[1])

    def test_guessGroup(self):
        candidates = (
            ("http://example.com", "example"),
            ("http://dev.example.com", "example"),
            ("http://stage.example.com", "example"),
            ("http://staging.example.com", "example"),
            ("http://somethingelse.example.com", "example"),
            ("http://sub1.sub2.sub3.example.co.uk", "example"),
            ("http://example.local", "example"),
            ("http://example", "example"),
        )

        for pair in candidates:
            result = self.controller.guessGroup(pair[0])
            self.assertEqual(result, pair[1])

    def extract_template_vars(self, mock):
        return mock.call_args[0][0]["html"][1]

    def test_guessName(self):
        candidates = (
            ("http://example.co.uk", "live"),
            ("http://dev.example.com", "dev"),
            ("http://stage.example.com", "stage"),
            ("http://staging.example.com", "staging"),
            ("http://somethingelse.example.com", "live"),
            ("http://sub1.sub2.sub3.example.co.uk", "live"),
            ("http://example.local", "local"),
            ("http://example", "dev"),
        )

        for pair in candidates:
            result = self.controller.guessName(pair[0])
            self.assertEqual(result, pair[1])

    @mock.patch("cherrypy.tools.negotiable._renderHtml")
    @mock.patch("cherrypy.engine.publish")
    def test_siteInGroup(self, publishMock, renderMock):
        """A request with a URL that belongs to known group returns
        equivalent URLs for other members of the group
        """

        def side_effect(*args, **kwargs):
            if (args[0] == "registry:first_key"):
                return ["example"]

            if (args[0] == "registry:search"):
                return [[
                    {
                        "rowid": 1,
                        "key": "bounce:example",
                        "value": "http://stage.example.com\nstage",
                    },
                    {
                        "rowid": 2,
                        "key": "bounce:example",
                        "value": "http://othersite.example.com\nothersite"
                    }
                ]]


        publishMock.side_effect = side_effect

        response = self.request("/", u="http://dev.example.com/with/subpath")

        template_vars = self.extract_template_vars(renderMock)

        self.assertEqual(template_vars["group"], "example")

        self.assertIsNone(template_vars["name"])

        self.assertEqual(template_vars["bounces"][1][0], "http://stage.example.com/with/subpath")
        self.assertEqual(template_vars["bounces"][1][1], "stage")

        self.assertEqual(template_vars["bounces"][2][0], "http://othersite.example.com/with/subpath")
        self.assertEqual(template_vars["bounces"][2][1], "othersite")

    @mock.patch("cherrypy.tools.negotiable._renderHtml")
    @mock.patch("cherrypy.engine.publish")
    def test_unrecognizedSite(self, publishMock, renderMock):
        """A request with a URL that does not belong to known group returns a form"""

        def side_effect(*args, **kwargs):
            if (args[0] == "registry:first_key"):
                return [None]

            if (args[0] == "registry:search"):
                return [None]

            if (args[0] == "registry:distinct_keys"):
                return [None]

        publishMock.side_effect = side_effect

        response = self.request("/", u="http://unrecognized.example.com")

        template_vars = self.extract_template_vars(renderMock)

        self.assertEqual(template_vars["group"], "example")

        self.assertEqual(template_vars["name"], "live")

        self.assertIsNone(template_vars["bounces"])
        self.assertEqual(template_vars["all_groups"], [])

    @mock.patch("cherrypy.tools.negotiable._renderHtml")
    @mock.patch("cherrypy.engine.publish")
    def test_bookmarkletUrlHonorsHttps(self, publishMock, renderMock):
        """If the site is served over HTTPs, the bookmarklet URL reflects that"""

        def side_effect(*args, **kwargs):
            if (args[0] == "registry:first_key"):
                return [None]

            if (args[0] == "registry:search"):
                return [None]

            if (args[0] == "registry:distinct_keys"):
                return [None]

        publishMock.side_effect = side_effect

        response = self.request(
            "/",
            headers={"X-HTTPS": "On"},
            u="http://unrecognized.example.com"
        )

        template_vars = self.extract_template_vars(renderMock)

        self.assertTrue(template_vars["app_url"].startswith("https"))

    @mock.patch("cherrypy.engine.publish")
    def test_addSite(self, publishMock):
        """A new site can be added to a group"""

        def side_effect(*args, **kwargs):
            if (args[0] == "registry:add"):
                return [{"uid": 1, "group": "example"}]

        publishMock.side_effect = side_effect

        response = self.request(
            "/",
            method="PUT",
            site="http://dev.example.com",
            group="example",
            name="dev",
        )

        self.assertEqual(response.code, 204)



if __name__ == "__main__":
    unittest.main()
