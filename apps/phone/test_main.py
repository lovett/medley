from testing import assertions
from testing import cptestcase
from testing import helpers
import unittest
import apps.phone.main
import mock

class TestPhone(cptestcase.BaseCherryPyTestCase, assertions.ResponseAssertions):

    @classmethod
    def setUpClass(cls):
        helpers.start_server(apps.phone.main.Controller)

    @classmethod
    def tearDownClass(cls):
        helpers.stop_server()

    @classmethod
    def tearDownClass(cls):
        helpers.stop_server()

    def extract_template_vars(self, mock, media="html"):
        return mock.call_args[0][0][media][1]

    def test_allow(self):
        """The app supports GET, PUT, and DELETE operations"""
        response = self.request("/", method="HEAD")
        self.assertAllowedMethods(response, ("GET",))

    @mock.patch("cherrypy.tools.negotiable._renderHtml")
    @mock.patch("cherrypy.engine.publish")
    def test_noNumber(self, publishMock, renderMock):
        """An HTML request with no number displays the search form"""

        def side_effect(*args, **kwargs):
            if args[0] == "phone:sanitize":
                return [None]

        publishMock.side_effect = side_effect
        self.request("/")
        template_vars = self.extract_template_vars(renderMock)
        self.assertFalse("error" in template_vars)

    @mock.patch("cherrypy.tools.negotiable._renderHtml")
    @mock.patch("cherrypy.engine.publish")
    def test_invalidNumberAsHtml(self, publishMock, renderMock):
        """An HTML request with an invalid number redirects with a message"""

        def side_effect(*args, **kwargs):
            if args[0] == "phone:sanitize":
                return [None]

        publishMock.side_effect = side_effect
        self.request("/", number="invalid-number-html")
        template_vars = self.extract_template_vars(renderMock)
        self.assertTrue("error" in template_vars)

    @mock.patch("cherrypy.engine.publish")
    def test_invalidNumberAsJson(self, publishMock):
        """A JSON request with an invalid number returns an error"""

        def side_effect(*args, **kwargs):
            if args[0] == "phone:sanitize":
                return [None]

        publishMock.side_effect = side_effect
        response = self.request("/", number="invalid-number-json", as_json=True)
        self.assertTrue(helpers.response_is_json(response))
        self.assertTrue("error" in response.body)

    @mock.patch("cherrypy.engine.publish")
    def test_invalidNumberAsText(self, publishMock):
        """A text/plain request with an invalid number returns an error"""

        def side_effect(*args, **kwargs):
            if args[0] == "phone:sanitize":
                return [None]

        publishMock.side_effect = side_effect
        response = self.request("/", number="invalid-number-text", as_text=True)
        self.assertTrue(helpers.response_is_text(response))
        self.assertEqual(response.body, apps.phone.main.Controller.messages["invalid"])


    @mock.patch("cherrypy.tools.negotiable._renderHtml")
    @mock.patch("cherrypy.engine.publish")
    def test_validNumber(self, publishMock, renderMock):
        def side_effect(*args, **kwargs):
            if args[0] == "cache:get":
                return [None]
            if args[0] == "geography:state_by_area_code":
                return [(None, "XY", None)]
            if args[0] == "geography:unabbreviate_state":
                return [(None, "Unabbreviated State")]
            if args[0] == "phone:sanitize":
                return ["1234567890"]
            if args[0] == "asterisk:is_blacklisted":
                return [False]
            if args[0] == "asterisk:get_caller_id":
                return [None]
            if args[0] == "cdr:call_history":
                return [[]]

        publishMock.side_effect = side_effect
        response = self.request("/", number="1234567890")
        template_vars = self.extract_template_vars(renderMock)
        self.assertEqual(template_vars["state_abbreviation"], "XY")

    @mock.patch("cherrypy.tools.negotiable._renderHtml")
    @mock.patch("cherrypy.engine.publish")
    def test_validNumberCached(self, publishMock, renderMock):
        def side_effect(*args, **kwargs):
            if args[0] == "cache:get":
                return [{
                    "state_lookup": ("query placeholder", "XY", None),
                    "state_name_lookup": ("query placeholder", "Unabbreviated State")
                }]
            if args[0] == "phone:sanitize":
                return ["1234567890"]
            if args[0] == "asterisk:is_blacklisted":
                return [False]
            if args[0] == "asterisk:get_caller_id":
                return [None]
            if args[0] == "cdr:call_history":
                return [[[{"clid": "test"}]]]

        publishMock.side_effect = side_effect
        response = self.request("/", number="1234567890")
        template_vars = self.extract_template_vars(renderMock)
        self.assertEqual(template_vars["state_abbreviation"], "XY")


if __name__ == "__main__":
    unittest.main()
