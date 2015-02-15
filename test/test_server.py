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
        "database.directory": tmp_dir,
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

    def test_ipNoToken(self):
        """ /ip without a token returns the caller's IP """
        response = self.request("/ip", headers={"Remote-Addr": "1.1.1.1"})
        self.assertEqual(response.code, 200)
        self.assertTrue("1.1.1.1" in response.body)

    def test_ipNoTokenJson(self):
        """ /ip returns json """
        response = self.request("/ip", headers={"Remote-Addr": "1.1.1.1"}, as_json=True)
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body["address"], "1.1.1.1")

    def test_ipNoTokenPlain(self):
        """ /ip returns text"""
        response = self.request("/ip", headers={"Remote-Addr": "1.1.1.1"}, as_plain=True)
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body, "1.1.1.1")

    def test_ipRightHeader(self):
        """ /ip prefers X-Real-Ip to Remote-Addr header """
        response = self.request("/ip", headers={
            "Remote-Addr": "1.1.1.1",
            "X-REAL-IP": "2.2.2.2"
        })
        self.assertTrue("2.2.2.2" in response.body)

    def test_ipValidTokenHtml(self):
        """ /ip returns html when a valid token is provided """
        cherrypy.config["ip.dns.command"] = []
        response = self.request("/ip/test")
        self.assertEqual(response.code, 200)
        self.assertTrue("<main" in response.body)

    def test_ipValidTokenJson(self):
        """ /ip returns json when a valid token is provided """
        cherrypy.config["ip.dns.command"] = []
        response = self.request("/ip/test", as_json=True)
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body["result"], "ok")

    def test_ipValidTokenPlain(self):
        """ /ip returns text when a valid token is provided """
        cherrypy.config["ip.dns.command"] = []
        headers = {
            "Remote-Addr": "1.1.1.1",
            "X-REAL-IP": "2.2.2.2"
        }
        response = self.request("/ip/test", headers=headers, as_plain=True)
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body, "ok")

    def test_ipValidTokenUpdatesDns(self):
        """ /ip calls the configured DNS update command via subprocess when a valid token is provided """
        remote_address = "127.0.0.1"
        token = "test2"
        host = "test2.example.com"
        expected_command = ["pdnsd-ctl", "add", "a", remote_address, host]
        configured_command = expected_command[:]
        configured_command[3] = "$ip"
        configured_command[4] = "$host"
        cherrypy.config["ip.dns.command"] = configured_command

        application = cherrypy.tree.apps[""]
        application.config["ip_tokens"][token] = host

        with mock.patch("medley.subprocess") as subprocess:
            response = self.request("/ip/" + token)
            subprocess.call.assert_called_once_with(expected_command)

    def test_ipInvalidToken(self):
        """ /ip fails when an invalid token is provided """
        response = self.request("/ip/invalid")
        self.assertEqual(response.code, 400)

    def test_ipInvalidTokenNoDns(self):
        """ /ip does not shell out when an invalid token is provided """
        with mock.patch("medley.subprocess") as subprocess:
            response = self.request("/ip/invalid")
            self.assertFalse(subprocess.called)

    def test_ipNoIp(self):
        """ /ip fails if the request ip can't be identified"""
        response = self.request("/ip/test", headers={"Remote-Addr": None})
        self.assertEqual(response.code, 400)

    def test_headersReturnsHtml(self):
        """ /headers returns html """
        response = self.request("/headers")
        self.assertEqual(response.code, 200)
        self.assertTrue("<table" in response.body)

    def test_headersReturnsJson(self):
        """ /headers returns json """
        response = self.request("/headers", as_json=True)
        self.assertEqual(response.code, 200)
        self.assertTrue("Accept" in response.body)

    def test_headersReturnsPlain(self):
        """ /headers returns text """
        response = self.request("/headers", as_plain=True)
        self.assertEqual(response.code, 200)
        self.assertTrue("Accept" in response.body)

    def test_headersNoArgs(self):
        """ /headers takes no arguments"""
        response = self.request("/headers/test")
        self.assertEqual(response.code, 404)

    def test_lettercaseReturnsHtml(self):
        """ /lettercase returns an HTML form"""
        response = self.request("/lettercase")
        self.assertEqual(response.code, 200)
        print("!" * 72)
        print(response.body)
        self.assertTrue("<form" in response.body)

    def test_lettercaseReturnsJson(self):
        """ /lettercase returns json """
        response = self.request("/lettercase", as_json=True)
        self.assertEqual(response.code, 200)
        self.assertTrue(response.body["result"] == "")

    def test_lettercaseConvertsToLowercase(self):
        """ /lettercase converts its input to lowercase """
        response = self.request(path="/lettercase",
                                method="POST",
                                as_plain=True,
                                style="lower",
                                value="TEST")
        self.assertEqual(response.body, "test")

    def test_lettercaseConvertsToUppercase(self):
        """ /lettercase converts its input to uppercase """
        response = self.request(path="/lettercase",
                                method="POST",
                                as_plain=True,
                                style="upper",
                                value="test")
        self.assertEqual(response.body, "TEST")

    def test_lettercaseConvertsToTitle(self):
        """ /lettercase converts its input to title case """
        response = self.request(path="/lettercase",
                                method="POST",
                                as_plain=True,
                                style="title",
                                value="this iS a TEst 1999")
        self.assertEqual(response.body, "This Is A Test 1999")

    def test_geodbReturns410IfNoUrl(self):
        """ /geodb returns 410 if geoip.download.url is not configured """
        cherrypy.config["geoip.download.url"] = None
        cherrypy.config["database.directory"] = "/tmp"
        response = self.request("/geodb")
        self.assertEqual(response.code, 410)

    def test_geodbReturns410IfNoDatabaseDirectory(self):
        """ /geodb returns 410 if database.directory is not configured """
        cherrypy.config["geoip.download.url"] = "http://example.com/test.gz"
        cherrypy.config["database.directory"] = None
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

    def test_whoisJsonWithoutAddress(self):
        """ /whois returns 400 if called as json without an address"""
        response = self.request("/whois", as_json=True)
        self.assertEqual(response.code, 400)
        self.assertTrue("message" in response.body)

    def test_whoisPlainWithoutAddress(self):
        """ /whois returns 400 if called as plain without an address"""
        response = self.request("/whois", as_plain=True)
        self.assertEqual(response.code, 400)

    @mock.patch("util.db.geoip")
    @mock.patch("util.net.whois")
    def test_whoisGeoipQuery(self, queryWhoisMock, geoipMock):
        """ /whois calls the geoip database """
        queryWhoisMock.return_value = {}
        geoipMock.return_value = {}
        ip = "1.1.1.1"
        response = self.request("/whois/" + ip, as_json=True)
        geoipMock.assert_called_once_with(ip)
        queryWhoisMock.assert_called_once_with(ip)

    @mock.patch("util.db.geoip")
    @mock.patch("util.net.whois")
    def test_whoisPopulateUsMapParams(self, queryWhoisMock, geoipMock):
        """ /whois defines the map region for a US IP as US-{state abbrev} """
        queryWhoisMock.return_value = {}
        geoipMock.return_value = {
            "country_code": "US",
            "region_code": "NY"
        }

        response = self.request("/whois/1.1.1.1", as_json=True)
        self.assertEqual(response.body["map_region"], "US-NY")

    @mock.patch("util.db.geoip")
    @mock.patch("util.net.whois")
    def test_whoisPopulateNonUsMapParams(self, queryWhoisMock, geoipMock):
        """ /whois defines the map region for a non-US IP as a 2-letter ISO code """
        queryWhoisMock.return_value = {}
        geoipMock.return_value = {
            "country_code": "AU"
        }
        response = self.request("/whois/1.1.1.1", as_json=True)
        self.assertEqual(response.body["map_region"], "AU")

    @mock.patch("util.db.geoip")
    @mock.patch("util.net.whois")
    def test_whoisSkipsGeoipQuery(self, queryWhoisMock, geoipMock):
        """ /whois returns success if the geoip query fails """
        queryWhoisMock.return_value = {}
        geoipMock.side_effect = Exception('Force fail')
        response = self.request("/whois/1.1.1.1", as_json=True)
        self.assertTrue(response.code, 200)


    @mock.patch("util.db.geoip")
    @mock.patch("util.net.whois")
    def test_whoisPlainReturnsCityAndCountry(self, queryWhoisMock, geoipMock):
        """ /whois returns the city and country name """
        queryWhoisMock.return_value = {}
        geoipMock.return_value = {
            "city": "test city",
            "country_code": "AA",
            "region_code": "BB",
            "country_name": "test country"
        }

        response = self.request("/whois/1.1.1.1", as_plain=True)
        self.assertEqual(response.body, "test city, test country")

    @mock.patch("util.db.geoip")
    @mock.patch("util.net.whois")
    def test_whoisPlainReturnsCountry(self, queryWhoisMock, geoipMock):
        """ /whois returns the county name if the city is not available"""
        geoipMock.return_value = {
            "country_code": "AA",
            "region_code": "BB",
            "country_name": "test country"
        }
        queryWhoisMock.return_value = {}
        response = self.request("/whois/1.1.1.1", as_plain=True)
        self.assertEqual(response.body, "test country")

    @mock.patch("util.db.geoip")
    @mock.patch("util.net.whois")
    def test_whoisPlainReturnsUnknown(self, queryWhoisMock, geoipMock):
        """ /whois returns "Unknown" if city and country name are not available"""
        geoipMock.return_value = {}
        queryWhoisMock.return_value = {}
        response = self.request("/whois/1.1.1.1", as_plain=True)
        self.assertEqual(response.body, "Unknown")

    @mock.patch("util.db.geoip")
    @mock.patch("util.net.whois")
    def test_whoisInputIp(self, queryWhoisMock, geoipMock):
        """ /whois accepts an IP address as input """
        queryWhoisMock.return_value = {}
        geoipMock.side_effect = Exception('Force fail')
        response = self.request("/whois/1.1.1.1", as_json=True)
        self.assertEqual(response.body["ip"], "1.1.1.1")

    @mock.patch("util.db.geoip")
    @mock.patch("util.net.resolveHost")
    @mock.patch("util.net.whois")
    def test_whoisInputHostname(self, whoisMock, resolveHostMock, geoipMock):
        """ /whois accepts a hostname as input """
        whoisMock.return_value = {}
        resolveHostMock.return_value = "1.1.1.1"
        geoipMock.side_effect = Exception('Force fail')
        response = self.request("/whois/example.com", as_json=True)
        self.assertEqual(response.body["ip"], "1.1.1.1")

    @mock.patch("util.db.geoip")
    @mock.patch("util.net.resolveHost")
    @mock.patch("util.net.whois")
    def test_whoisInputUrl(self, whoisMock, resolveHostMock, geoipMock):
        """ /whois accepts a full URL as input """
        whoisMock.return_value = {}
        resolveHostMock.return_value = "1.1.1.1"
        geoipMock.side_effect = Exception('Force fail')
        response = self.request("/whois/example.com", as_json=True)
        self.assertEqual(response.body["ip"], "1.1.1.1")
        self.assertEqual(response.body["address"], "example.com")

    @mock.patch("util.db.geoip")
    @mock.patch("util.net.resolveHost")
    @mock.patch("util.net.whois")
    def test_whoisInputHostAlias(self, whoisMock, resolveHostMock, geoipMock):
        """ /whois accepts a host alias as input """
        whoisMock.return_value = {}
        resolveHostMock.return_value = "1.1.1.1"
        geoipMock.side_effect = Exception('Force fail')
        response = self.request("/whois/foo", as_json=True)
        self.assertEqual(response.body["ip"], "1.1.1.1")

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

    @mock.patch("medley.util.net.externalIp")
    def test_externalIpSuccess(self, externalIp):
        """/external-ip returns 204 on success"""
        cherrypy.request.app.config["ip_tokens"]["external"] = "external.example.com"
        cherrypy.config["ip.dns.command"] = []
        address = "1.1.1.1"
        externalIp.return_value = address
        response = self.request("/external-ip")


    @mock.patch("medley.util.net.externalIp")
    def test_externalIpFail(self, externalIp):
        """/external-ip returns "not available" when the
        DNS-O-Matic query fails"""
        cherrypy.request.app.config["ip_tokens"]["external"] = "external.example.com"
        externalIp.side_effect = medley.util.net.NetException("Force fail")
        response = self.request("/external-ip")
        self.assertEqual(response.code, 500)

    @mock.patch("medley.util.net.externalIp")
    def test_externalIpNoHost(self, externalIp):
        """/external-ip returns 500 if an external hostname has not been defined"""
        cherrypy.request.app.config["ip_tokens"]["external"] = None
        externalIp.return_value = None

        response = self.request("/external-ip", as_plain=True)
        self.assertEqual(response.code, 500)

    @mock.patch("medley.util.net.externalIp")
    def test_externalIpUpdatesDns(self, externalIp):
        """/external-ip updates the local DNS server, setting the
        IP returned by DNS-O-Matic to the valid of the ip token "external"."""
        address = "1.1.1.1"
        host = "external.example.com"
        expected_command = ["pdnsd-ctl", "add", "a", address, host]

        configured_command = expected_command[:]
        configured_command[3] = "$ip"
        configured_command[4] = "$host"

        cherrypy.config["ip.dns.command"] = configured_command
        cherrypy.request.app.config["ip_tokens"]["external"] = host

        externalIp.return_value = address

        application = cherrypy.tree.apps[""]
        application.config["ip_tokens"]["external"] = host

        with mock.patch("medley.subprocess") as subprocess:
            response = self.request("/external-ip")
            subprocess.call.assert_called_once_with(expected_command)

    def test_dnsmatchNoToken(self):
        """/dnsmatch requires a URL token to determine which
        hosts to check."""
        response = self.request("/dnsmatch")
        self.assertEqual(response.code, 400)

    def test_dnsmatchInvalidToken(self):
        """/dnsmatch rejects URL tokens that are not in the config."""
        response = self.request("/dnsmatch/foo")
        self.assertEqual(response.code, 400)

    def test_dnsmatchOk(self):
        """ /dnsmatch returns ok if there is no mismatch"""
        with mock.patch("medley.subprocess.Popen") as popen:
            popen.return_value.communicate.side_effect = [(b"foo", None), (b"foo", None)]
            response = self.request("/dnsmatch/test", as_json=True)
            self.assertTrue("result" in response.body)
            self.assertTrue("commands" in response.body)
            self.assertTrue("command_results" in response.body)
            self.assertEqual(response.body["result"], "ok")

    def test_dnsmatchSilent(self):
        """ /dnsmatch returns 204 in silent mode"""
        with mock.patch("medley.subprocess.Popen") as popen:
            popen.return_value.communicate.side_effect = [(b"foo", None), (b"foo", None)]
            response = self.request("/dnsmatch/test", silent=1)
            self.assertEqual(response.body, "")
            self.assertEqual(response.code, 204)

    def test_dnsmatchOkPlain(self):
        """ /dnsmatch returns ok if there is no mismatch"""
        with mock.patch("medley.subprocess.Popen") as popen:
            popen.return_value.communicate.side_effect = [(b"foo", None), (b"foo", None)]
            response = self.request("/dnsmatch/test", as_plain=True)
            self.assertEqual(response.body, "ok")

    def test_dnsmatchMismatch(self):
        """ /dnsmatch returns a mismatch"""
        with mock.patch("medley.subprocess.Popen") as popen:
            popen.return_value.communicate.side_effect = [(b"foo", None), (b"bar", None)]
            response = self.request("/dnsmatch/test", as_json=True)
            self.assertTrue("result" in response.body)
            self.assertTrue("commands" in response.body)
            self.assertTrue("command_results" in response.body)
            self.assertEqual(response.body["result"], "mismatch")

    @mock.patch("util.net.sendMessage")
    def test_dnsmatchEmailOnlyOnPost(self, sendMessage):
        """ /dnsmatch sends email on post requests"""
        with mock.patch("medley.subprocess.Popen") as popen:
            popen.return_value.communicate.side_effect = [(b"foo", None), (b"bar", None)]
            response = self.request("/dnsmatch/test", as_json=True)
            self.assertFalse(sendMessage.called)

    @mock.patch("util.net.sendMessage")
    def test_dnsmatchSendEmail(self, sendMessage):
        """ /dnsmatch sends email"""
        sendMessage.return_value = True

        with mock.patch("medley.subprocess.Popen") as popen:
            popen.return_value.communicate.side_effect = [(b"foo", None), (b"bar", None)]

            response = self.request(path="/dnsmatch/test",
                                    method="POST",
                                    email=1)
            self.assertTrue(sendMessage.called)

            args = sendMessage.call_args_list[0][0][0]

            for key, value in args.items():
                self.assertTrue(value is not None)


if __name__ == "__main__":
    import unittest
    unittest.main()
