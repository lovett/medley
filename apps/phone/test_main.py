from testing import cptestcase
import datetime
from testing import helpers
import unittest
import responses
import apps.phone.main
import mock
import util.cache
import util.phone
import time
import shutil
import tempfile
import cherrypy
import os.path

class TestTopics(cptestcase.BaseCherryPyTestCase):
    temp_dir = None

    @classmethod
    def setUpClass(cls):
        helpers.start_server(apps.phone.main.Controller)

    @classmethod
    def tearDownClass(cls):
        helpers.stop_server()

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="phone-test")
        cherrypy.config["database_dir"] = self.temp_dir
        cherrypy.config["asterisk.cdr_db"] = os.path.join(self.temp_dir, "cdr.db")

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    @mock.patch("util.cache.Cache.get")
    def test_returnsHtml(self, cacheGetMock):
        """It returns HTML"""
        response = self.request("/")
        self.assertEqual(response.code, 200)
        self.assertTrue(helpers.response_is_html(response))
        self.assertTrue("<main" in response.body)
        self.assertFalse(cacheGetMock.called)

    @mock.patch("util.cache.Cache.get")
    def test_returnsErrorJson(self, cacheGetMock):
        """A json request that does not specify a number returns an error"""
        response = self.request("/", as_json=True)
        self.assertEqual(response.code, 400)
        self.assertTrue(helpers.response_is_json(response))
        self.assertTrue("message" in response.body)
        self.assertFalse(cacheGetMock.called)

    @mock.patch("util.cache.Cache.get")
    def test_returnsErrorText(self, cacheGetMock):
        """A text/plain request that does not specify a number returns an error"""
        response = self.request("/", as_plain=True)
        self.assertEqual(response.code, 400)
        self.assertFalse(cacheGetMock.called)

    @mock.patch("util.phone.sanitize")
    @mock.patch("util.cache.Cache.get")
    def test_rejectsInvalidNumber(self, cacheGetMock, sanitizeMock):
        """Rejects invalid phone number"""
        sanitizeMock.return_value = "1"
        response = self.request("/", number=1)
        self.assertEqual(response.code, 400)
        self.assertFalse(cacheGetMock.called)

    @mock.patch("util.phone.sanitize")
    @mock.patch("util.cache.Cache.get")
    def test_rejectsInvalidNumberJson(self, cacheGetMock, sanitizeMock):
        """Rejects invalid phone number"""
        sanitizeMock.return_value = "1"
        response = self.request("/", number=1, as_json=True)
        self.assertEqual(response.code, 400)
        self.assertTrue("message" in response.body)
        self.assertFalse(cacheGetMock.called)

    @mock.patch("apps.phone.models.AsteriskCdr.callHistory")
    @mock.patch("apps.phone.models.AsteriskManager.isBlackListed")
    @mock.patch("apps.phone.models.AsteriskManager.getCallerId")
    @mock.patch("apps.phone.models.AsteriskManager.authenticate")
    @mock.patch("util.phone.sanitize")
    @mock.patch("util.cache.Cache.get")
    def test_cacheHit(self, cacheGetMock, sanitizeMock, authenticateMock, cidMock, blacklistMock, historyMock):
        """Cached values from a previous lookup are successfully retrieved"""
        cacheGetMock.return_value = ({"state_abbreviation": "NY"},)
        sanitizeMock.return_value = "1234567890"
        authenticateMock.return_value = True
        cidMock.return_value = "test"
        blacklistMock.return_value = False
        historyMock.return_value = []
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
    def test_cacheMiss(self, cacheGetMock, sanitizeMock, authenticateMock, cidMock, blacklistMock, historyMock, areaCodeMock, cacheSetMock):
        """A cache miss triggers an area code lookup"""
        cacheGetMock.return_value = None
        areaCodeMock.return_value = {"state_abbreviation": "NY"}
        sanitizeMock.return_value = "1234567890"
        authenticateMock.return_value = True
        cidMock.return_value = None
        blacklistMock.return_value = False
        historyMock.return_value = [[{
            "date": "",
            "duration": 1,
            "lastapp": "test",
            "dst": 1
        }]]
        response = self.request("/", number="1234567890")
        self.assertEqual(response.code, 200)
        self.assertTrue("message" in response.body)
        self.assertTrue(cacheGetMock.called)
        self.assertTrue(authenticateMock.called)
        self.assertTrue(cacheSetMock)


if __name__ == "__main__":
    unittest.main()
