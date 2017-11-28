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

    @mock.patch("util.cache.Cache.get")
    def xtest_withoutNumberAsHtml(self, cacheGetMock):
        """An HTML request that does not specify a nubmer returns a search form"""
        response = self.request("/")
        self.assertEqual(response.code, 200)
        self.assertTrue(helpers.response_is_html(response))
        self.assertTrue("<form" in response.body)
        self.assertFalse(cacheGetMock.called)

    @mock.patch("util.cache.Cache.get")
    def xtest_withoutNumberAsJson(self, cacheGetMock):
        """A json request that does not specify a number returns an error"""
        response = self.request("/", as_json=True)
        self.assertEqual(response.code, 400)
        self.assertIn("message", response.body)
        self.assertFalse(cacheGetMock.called)

    @mock.patch("util.cache.Cache.get")
    def xtest_withoutNumberAsText(self, cacheGetMock):
        """A text/plain request that does not specify a number returns an error"""
        response = self.request("/", as_plain=True)
        self.assertEqual(response.code, 400)
        self.assertFalse(cacheGetMock.called)

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

    @mock.patch("apps.phone.models.AsteriskCdr.callHistory")
    @mock.patch("apps.phone.models.AsteriskManager.isBlackListed")
    @mock.patch("apps.phone.models.AsteriskManager.getCallerId")
    @mock.patch("apps.phone.models.AsteriskManager.authenticate")
    @mock.patch("util.phone.sanitize")
    @mock.patch("util.cache.Cache.get")
    def xtest_cacheHit(self, cacheGetMock, sanitizeMock, authenticateMock, cidMock, blacklistMock, historyMock):
        """Cached values from a previous lookup are successfully retrieved"""
        cacheGetMock.return_value = ({"state_abbreviation": "NY"},)
        sanitizeMock.return_value = "1234567890"
        authenticateMock.return_value = True
        cidMock.return_value = "test"
        blacklistMock.return_value = False
        historyMock.return_value = ([], 0)
        response = self.request("/", number="1234567890")

        self.assertEqual(response.code, 200)
        self.assertTrue("message" in response.body)
        self.assertTrue(cacheGetMock.called)
        self.assertTrue(authenticateMock.called)

    @mock.patch("util.cache.Cache.set")
    @mock.patch("util.phone.findAreaCode")
    @mock.patch("apps.phone.models.AsteriskCdr.callHistory")
    @mock.patch("apps.phone.models.AsteriskManager.isBlackListed")
    @mock.patch("apps.phone.models.AsteriskManager.getCallerId")
    @mock.patch("apps.phone.models.AsteriskManager.authenticate")
    @mock.patch("util.phone.sanitize")
    @mock.patch("util.cache.Cache.get")
    def xtest_cacheMiss(self, cacheGetMock, sanitizeMock, authenticateMock, cidMock, blacklistMock, historyMock, areaCodeMock, cacheSetMock):
        """A cache miss triggers an area code lookup"""
        cacheGetMock.return_value = None
        areaCodeMock.return_value = {"state_abbreviation": "NY"}
        sanitizeMock.return_value = "1234567890"
        authenticateMock.return_value = True
        cidMock.return_value = None
        blacklistMock.return_value = False
        historyMock.return_value = ([{
            "date": "",
            "duration": 1,
            "lastapp": "test",
            "dst": 1,
            "clid": "test"
        }], 1)
        response = self.request("/", number="1234567890")
        self.assertEqual(response.code, 200)
        self.assertTrue("message" in response.body)
        self.assertTrue(cacheGetMock.called)
        self.assertTrue(authenticateMock.called)
        self.assertTrue(cacheSetMock)

    @mock.patch("util.cache.Cache.set")
    @mock.patch("util.phone.findAreaCode")
    @mock.patch("apps.phone.models.AsteriskCdr.callHistory")
    @mock.patch("apps.phone.models.AsteriskManager.authenticate")
    @mock.patch("util.phone.sanitize")
    @mock.patch("util.cache.Cache.get")
    def xtest_asteriskManagerAuthFail(self, cacheGetMock, sanitizeMock, authenticateMock, historyMock, areaCodeMock, cacheSetMock):
        cacheGetMock.return_value = None
        areaCodeMock.return_value = {"state_abbreviation": "NY"}
        sanitizeMock.return_value = "1234567890"
        authenticateMock.return_value = False
        historyMock.return_value = ([{
            "date": "",
            "duration": 1,
            "lastapp": "test",
            "dst": 1,
            "clid": "test"
        }], 1)
        response = self.request("/", number="1234567890")
        self.assertEqual(response.code, 200)
        self.assertTrue(cacheGetMock.called)
        self.assertTrue(authenticateMock.called)
        self.assertTrue(cacheSetMock)


if __name__ == "__main__":
    unittest.main()
