import cherrypy
import os.path
import json
import pytest
import util.net
import urllib.parse
import mock
import medley
import tempfile
from cptestcase import BaseCherryPyTestCase

def setup_module():

    tmp_dir = tempfile.gettempdir()

    # The test config is based on the sample config, with overrides as needed
    config_file = os.path.realpath("default.conf")
    cherrypy.config.update(config_file)
    cherrypy.config.update({
        "log.screen": False,
        "database_dir": tmp_dir,
        "azure.url.deployments": "http://example.com/{}/deployments",
        "tools.conditional_auth.on": False,
        "users": {"test":"test"},
        "cache.backend": "dogpile.cache.null"
    })

    # Application config entries are also taken from medley.conf and
    # then overridden. It might seem like the global config would be
    # reverted, but the global section of the file is skipped.
    app = cherrypy.tree.mount(medley.MedleyServer(), script_name="",
                              config=config_file)

    # Application config overrides
    app.merge({
        "dns_hosts": {
            "test": ["foo", "bar"]
        },
        "ip_tokens": {
            "external": "external.example.com",
            "test": "test.example.com"
        }
    })

    cherrypy.engine.start()

def teardown_module():
    cherrypy.engine.exit()

class TestMedleyServer(BaseCherryPyTestCase):
    app = None
    config = None

    def setup_method(self, method):
        self.app = cherrypy.tree.apps['']
        self._config = self.app.config

    def teardown_method(self, method):
        self.app.config = self._config

    def test_htmlCharset(self):
        """Requests for text/html specify charset=utf-8. Since the
        charset is applied to all requests via the negotiable tool,
        only the index endpoint is tested"""
        response = self.request("/")
        self.assertEqual(response.headers["content-type"], "text/html;charset=utf-8")

    def test_plainCharset(self):
        """Requests for text/plain specify charset=utf-8. Since the
        charset is applied to all requests via the negotiable tool,
        only the index endpoint is tested"""
        response = self.request("/", as_plain=True)
        self.assertEqual(response.headers["content-type"], "text/plain;charset=utf-8")

    def test_jsonCharset(self):
        """Requests for application/json do not specify a charset in the
        content-type header. Since the charset is applied to all
        requests via the negotiable tool, only the index endpoint is
        tested"""
        response = self.request("/", as_json=True)
        self.assertEqual(response.headers["content-type"], "application/json")

    def test_endpointsReturnHTML(self):
        """Endpoints return HTML by default"""
        response = self.request("/")
        self.assertEqual(response.code, 200)
        self.assertTrue("<main" in response.body)

    def test_azure410IfNoNotifierUrl(self):
        """ /azure returns 410 if notifier endpoint is not defined """
        self.app.config["notifier"] = {}
        response = self.request("/azure/foo")
        self.assertEqual(response.code, 410)

    def test_azure404IfNoEvent(self):
        """ /azure returns 404 if the event segment is not in the request url """
        response = self.request("/azure")
        self.assertEqual(response.code, 404)

    def test_azureRejectsFormPost(self):
        """ /azure rejects application/x-www-form-urlencoded"""
        response = self.request(path="/azure/test",
                                method="POST",
                                foo="bar")

        self.assertEqual(response.code, 415)

    @mock.patch("medley.util.net.sendNotification")
    def test_azureRejectsUnexpectedJson(self, sendNotificationMock):
        """ /azure rejects json with unexpected fields """
        self.app.config["notifier"] = {
            "endpoint": "http://example.com"
        }

        response = self.request(path="/azure/test",
                                method="POST",
                                data=json.dumps({"foo":"bar"}).encode("utf-8"),
                                headers={"Content-type": "application/json"})
        self.assertFalse(sendNotificationMock.called)
        self.assertEqual(response.code, 400)


    @mock.patch("medley.util.net.sendNotification")
    def test_azureNotificationTitleSuccess(self, sendNotificationMock):
        """ /azure sends a success notification """
        sendNotificationMock.return_value = True

        self.app.config["notifier"] = {
            "endpoint": "http://example.com"
        }

        body = {
            "siteName": "foo",
            "status": "success",
            "complete": True
        }

        response = self.request(path="/azure/test",
                                method="POST",
                                data=json.dumps(body).encode("utf-8"),
                                headers={"Content-type": "application/json"})

        notification = sendNotificationMock.call_args[0][0]
        self.assertEqual(notification["title"], "Deployment to foo is complete")

    @mock.patch("medley.util.net.sendNotification")
    def test_azureNotificationTitleFail(self, sendNotificationMock):
        """ /azure sends a failure notification """
        self.app.config["notifier"] = {
            "endpoint": "http://example.com"
        }

        body = {
            "siteName": "foo",
            "status": "failed",
            "complete": True
        }

        response = self.request(path="/azure/test",
                                method="POST",
                                data=json.dumps(body).encode("utf-8"),
                                headers={"Content-type": "application/json"})

        notification = sendNotificationMock.call_args[0][0]
        self.assertEqual(notification["title"], "Deployment to foo has failed")

    @mock.patch("medley.util.net.sendNotification")
    def test_azureNotificationTitleOther(self, sendNotificationMock):
        """ /azure handles status values other than success and failure"""

        self.app.config["notifier"] = {
            "endpoint": "http://example.com"
        }

        body = {
            "siteName": "foo",
            "status": "argle bargle",
            "complete": True
        }

        response = self.request(path="/azure/test",
                                method="POST",
                                data=json.dumps(body).encode("utf-8"),
                                headers={"Content-type": "application/json"})

        notification = sendNotificationMock.call_args[0][0]
        self.assertEqual(notification["title"], "Deployment to foo is argle bargle")

    @mock.patch("medley.util.net.sendNotification")
    def test_azureNotificationIncludesExpectedValues(self, sendNotificationMock):
        """ /azure notifications link to the management console and set group to azure"""

        self.app.config["notifier"] = {
            "endpoint": "http://example.com"
        }

        body = {
            "siteName": "foo",
            "status": "success",
            "complete": True
        }

        response = self.request(path="/azure/test",
                                method="POST",
                                data=json.dumps(body).encode("utf-8"),
                                headers={"Content-type": "application/json"})

        notification = sendNotificationMock.call_args[0][0]
        self.assertTrue(body["siteName"] in notification["title"])
        self.assertEqual(notification["group"], "azure")

    @mock.patch("medley.util.net.sendNotification")
    def test_azureMessageFirstLine(self, sendNotificationMock):
        """/azure notification bodies truncate the commit message"""

        self.app.config["notifier"] = {
            "endpoint": "http://example.com"
        }

        body = {
            "siteName": "foo",
            "status": "success",
            "message": "line1 foo bar\nline2 foo bar \nline3 foo bar",
            "complete": True
        }

        response = self.request(path="/azure/test",
                                method="POST",
                                data=json.dumps(body).encode("utf-8"),
                                headers={"Content-type": "application/json"})

        notification = sendNotificationMock.call_args[0][0]
        self.assertEqual(notification["body"], "line1 foo bar")

    @mock.patch("medley.util.net.sendNotification")
    def test_azurePublicAccess(self, sendNotificationMock):
        """ /azure does not require authentication"""

        self.app.config["notifier"] = {
            "endpoint": "http://example.com"
        }

        headers = {
            "Remote-Addr": "127.0.0.2",
            "Content-type": "application/json"
        }

        body = {
            "siteName": "foo",
            "status": "success",
            "message": "line1 foo bar\nline2 foo bar \nline3 foo bar",
            "complete": True
        }

        response = self.request(path="/azure/test",
                                method="POST",
                                data=json.dumps(body).encode("utf-8"),
                                headers=headers)
        self.assertEqual(response.code, 200)

    @mock.patch("medley.util.net.sendNotification")
    def test_azureMalformedRequest(self, sendNotificationMock):
        """ /azure rejects a request with malformed JSON"""

        self.app.config["notifier"] = {
            "endpoint": "http://example.com"
        }

        response = self.request(path="/azure/test",
                                method="POST",
                                data="{\"foo".encode("utf-8"),
                                headers={"Content-type": "application/json"})

        self.assertFalse(sendNotificationMock.called)
        self.assertEqual(response.code, 400)


    def test_favicon(self):
        """/favicon.ico does not require authentication and is returned as an image"""
        response = self.request(path="/favicon.ico")
        self.assertEqual(response.code, 200)
        self.assertEqual(response.headers["Content-Type"], "image/x-icon")

    def test_indexReturnsJson(self):
        """ / returns json"""
        response = self.request("/", as_json=True)
        self.assertEqual(response.code, 200)
        self.assertEqual(response.headers["content-type"], "application/json")
        self.assertTrue(len(response.body) > 0)

    def test_indexReturnsPlain(self):
        """ / returns text"""
        response = self.request("/", as_plain=True)
        self.assertEqual(response.code, 200)
        self.assertTrue("/" in response.body)

    def test_geodbReturns410IfNoUrl(self):
        """/geodb returns 410 if geoip.download.url is not configured """
        cherrypy.config["geoip.download.url"] = None
        cherrypy.config["database_dir"] = "/tmp"
        response = self.request("/geodb")
        self.assertEqual(response.code, 410)

    def test_geodbReturns410IfNoDatabaseDirectory(self):
        """ /geodb returns 410 if database_dir is not configured """
        cherrypy.config["geoip.download.url"] = "http://example.com/test.gz"
        cherrypy.config["database_dir"] = None
        response = self.request("/geodb")
        self.assertEqual(response.code, 410)

    @mock.patch("medley.urllib.request")
    def test_geodbReturns500IfGunzipFails(self, requestMock):
        """ /geodb returns 500 if the database cannot be gunzipped."""
        cherrypy.config["geoip.download.url"] = "http://example.com/test.gz"
        response = self.request("/geodb/update", method="POST")
        self.assertFalse(requestMock.urlopen.called)
        self.assertEqual(response.code, 500)

    @mock.patch("medley.subprocess")
    @mock.patch("medley.util.net.saveUrl")
    def test_geodbReturns204(self, saveUrlMock, subprocessMock):
        """ /geodb returns 204 if the database is successfully downloaded  """
        cherrypy.config["geoip.download.url"] = "http://example.com/test.gz"
        saveUrlMock.return_value = True
        subprocessMock.check_call.return_value = 0
        response = self.request("/geodb/update", method="POST")
        self.assertTrue(saveUrlMock.called)
        self.assertEqual(response.code, 204)

    def test_phoneNoNumberJson(self):
        """ /phone returns 400 if called as json without a number"""
        response = self.request("/phone", as_json=True)
        self.assertEqual(response.code, 400)
        self.assertTrue("message" in response.body)

    def test_phoneNoNumberPlain(self):
        """ /phone returns 400 if called as text without a number """
        response = self.request("/phone", as_plain=True)
        self.assertEqual(response.code, 400)

    def test_phoneInvalidNumberJson(self):
        """ /phone returns 400 if called as json with an invalid number """
        response = self.request("/phone/1", as_json=True)
        self.assertEqual(response.code, 400)
        self.assertTrue("message" in response.body)

    def test_phoneInvalidNumberPlain(self):
        """ /phone returns 400 if called as plain with an invalid number """
        response = self.request("/phone/1", as_plain=True)
        self.assertEqual(response.code, 400)

    @mock.patch("medley.util.phone")
    def test_phoneValidAreaCodeJson(self, phoneMock):
        """/phone returns the state name of the given area code as json"""

        phoneMock.callHistory.return_value = ([], 0)
        phoneMock.findAreaCode.return_value = {"state_name": "New York"}
        phoneMock.sanitize.return_value = "212"
        phoneMock.format.return_value = "212"
        response = self.request("/phone/212", as_json=True)
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body["state_name"], "New York")
        self.assertTrue(phoneMock.callHistory.called_once)
        self.assertTrue(phoneMock.findAreaCode.called_once)
        self.assertTrue(phoneMock.santize.called_once)

    @mock.patch("medley.util.phone")
    def test_phoneValidAreaCodePlain(self, phoneMock):
        """/phone returns the state name of the given area code as text"""

        phoneMock.callHistory.return_value = ([], 0)
        phoneMock.findAreaCode.return_value = {"state_name": "New York"}
        phoneMock.sanitize.return_value = "212"
        phoneMock.format.return_value = "212"
        response = self.request("/phone/212", as_plain=True)
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body, "New York")
        self.assertTrue(phoneMock.callHistory.called_once)
        self.assertTrue(phoneMock.findAreaCode.called_once)
        self.assertTrue(phoneMock.santize.called_once)

    @mock.patch("medley.util.phone")
    def test_phoneInvalidAreaCodeJson(self, phoneMock):
        """/phone returns None as json if the area code is invalid"""

        phoneMock.callHistory.return_value = ([], 0)
        phoneMock.findAreaCode.return_value = {"state_name": None}
        phoneMock.sanitize.return_value = "212"
        phoneMock.format.return_value = "212"
        response = self.request("/phone/212", as_json=True)
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body["state_name"], None)
        self.assertTrue(phoneMock.callHistory.called_once)
        self.assertTrue(phoneMock.findAreaCode.called_once)
        self.assertTrue(phoneMock.santize.called_once)

    @mock.patch("medley.util.phone")
    def test_phoneInvalidAreaCodeText(self, phoneMock):
        """/phone returns None as text if the area code is invalid"""

        phoneMock.callHistory.return_value = ([], 0)
        phoneMock.findAreaCode.return_value = {"state_name": "Unknown"}
        phoneMock.sanitize.return_value = "212"
        phoneMock.format.return_value = "212"
        response = self.request("/phone/212", as_plain=True)
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body, "Unknown")
        self.assertTrue(phoneMock.callHistory.called_once)
        self.assertTrue(phoneMock.findAreaCode.called_once)
        self.assertTrue(phoneMock.santize.called_once)


if __name__ == "__main__":
    import unittest
    unittest.main()
