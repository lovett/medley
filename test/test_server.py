import cherrypy
import os.path
import json
import httpretty
import helpers
import urllib.parse
import mock
from medley import MedleyServer
from cptestcase import BaseCherryPyTestCase

@mock.patch("medley.memcache.Client")
def setup_module(memcacheClient):
    config_file = os.path.realpath("medley.conf")
    cherrypy.config.update(config_file)

    # Force all get and set calls to memcache to return None
    instance = memcacheClient.return_value
    instance.get.return_value = None
    instance.set.return_value = None

    app = cherrypy.tree.mount(MedleyServer(), script_name="", config=config_file)

    config_extra = {
        "global": {
            "request.show_tracebacks": False,
            "azure.url.deployments": "http://example.com/{}/deployments",
        },
        "dns_hosts": {
            "test": ["foo", "bar"]
        },
        "/ip": {
            "tools.auth_basic.checkpassword": cherrypy.lib.auth_basic.checkpassword_dict({
                "test":"test"
            })
        },
        "ip_tokens": {
            "external": "external.example.com",
            "test": "test.example.com"
        }
    }

    cherrypy.config.update(config_extra)
    app.merge(config_extra)

    cherrypy.engine.start()

def teardown_module():
    cherrypy.engine.exit()

class TestMedleyServer(BaseCherryPyTestCase):
    def test_htmlCharset(self):
        """Requests for text/html content specify charset=utf-8.  Since the
        charset is applied to all requests via the negotiable tool,
        only the index endpoint is tested"""
        response = self.request("/")
        self.assertEqual(response.headers["content-type"], "text/html;charset=utf-8")

    def test_plainCharset(self):
        """Requests for text/plain specify charset=utf-8. Only the index endpoint is tested"""
        response = self.request("/", as_plain=True)
        self.assertEqual(response.headers["content-type"], "text/plain;charset=utf-8")

    def test_jsonCharset(self):
        """Requests for application/json do not specify a charset in the content-type header. Only the index endpoint is tested"""
        response = self.request("/", as_json=True)
        self.assertEqual(response.headers["content-type"], "application/json")

    def test_endpointsReturnHTML(self):
        """ Endpoints return HTML by default """
        headers = {
            "Remote-Addr": "1.1.1.1",
        }

        endpoints = ["/", "/ip", "/headers", "/phone", "/whois"]
        for endpoint in endpoints:
            response = self.request(endpoint, headers=headers)
            self.assertEqual(response.code, 200)
            self.assertTrue("<main" in response.body)


    def test_azure410IfNoNotifierUrl(self):
        """ The azure endpoints returns 410 if notifier.url is not configured """
        cherrypy.config["notifier.url"] = None
        response = self.request("/azure/foo")
        self.assertEqual(response.code, 410)

    def test_azure404IfNoEvent(self):
        """ The azure endpoint returns 404 if the event segment is not in the request url """
        response = self.request("/azure")
        self.assertEqual(response.code, 404)

    def test_azureRejectsFormPost(self):
        """ The azure endpoint rejects application/x-www-form-urlencoded"""
        response = self.request(path="/azure/test",
                                method="POST",
                                foo="bar")

        self.assertEqual(response.code, 415)

    @httpretty.activate
    def test_azureRejectsUnexpectedJson(self):
        """ The azure endpoint rejects json requests without expected fields """

        cherrypy.config["notifier.url"] = "http://example.com"

        httpretty.register_uri(httpretty.POST, cherrypy.config["notifier.url"])

        headers = {
            "Content-type": "application/json"
        }

        body = {
            "foo": "bar"
        }

        response = self.request(path="/azure/test",
                                method="POST",
                                data=json.dumps(body).encode("utf-8"),
                                headers=headers)

        self.assertEqual(response.code, 400)

        body = {
            "siteName": "foo"
        }

        response = self.request(path="/azure/test",
                                method="POST",
                                data=json.dumps(body).encode("utf-8"),
                                headers=headers)

        self.assertEqual(response.code, 200)

    @httpretty.activate
    def test_azureNotificationTitleSuccess(self):
        """ The azure endpoint's notification indicates success in the title """

        cherrypy.config["notifier.url"] = "http://example.com"

        httpretty.register_uri(httpretty.POST, cherrypy.config["notifier.url"])

        headers = {
            "Content-type": "application/json"
        }

        body = {
            "siteName": "foo",
            "status": "success",
            "complete": True
        }

        response = self.request(path="/azure/test",
                                method="POST",
                                data=json.dumps(body).encode("utf-8"),
                                headers=headers)

        self.assertEqual(httpretty.last_request().parsed_body["title"][0], "Deployment to foo is complete")

    @httpretty.activate
    def test_azureNotificationTitleFail(self):
        """ The azure endpoint's notification indicates failure in the title """

        cherrypy.config["notifier.url"] = "http://example.com"

        httpretty.register_uri(httpretty.POST, cherrypy.config["notifier.url"])

        headers = {
            "Content-type": "application/json"
        }

        body = {
            "siteName": "foo",
            "status": "failed",
            "complete": True
        }

        response = self.request(path="/azure/test",
                                method="POST",
                                data=json.dumps(body).encode("utf-8"),
                                headers=headers)

        self.assertEqual(httpretty.last_request().parsed_body["title"][0], "Deployment to foo has failed")

    @httpretty.activate
    def test_azureNotificationIncludesExpectedValues(self):
        """ The azure endpoint notification links to the management console, and sets group to azure """

        cherrypy.config["notifier.url"] = "http://example.com"

        httpretty.register_uri(httpretty.POST, cherrypy.config["notifier.url"])

        headers = {
            "Content-type": "application/json"
        }

        body = {
            "siteName": "foo",
            "status": "success",
            "complete": True
        }

        response = self.request(path="/azure/test",
                                method="POST",
                                data=json.dumps(body).encode("utf-8"),
                                headers=headers)

        print(httpretty.last_request().parsed_body)
        self.assertTrue(body["siteName"] in httpretty.last_request().parsed_body["url"][0])
        self.assertEqual(httpretty.last_request().parsed_body["group"][0], "azure")

    @httpretty.activate
    @mock.patch("medley.urllib.request.Request")
    def test_azureMessageFirstLine(self, requestMock):
        """The body of the notification sent by the azure endpoint only
        contains the first line of the commit message."""

        cherrypy.config["notifier.url"] = "http://example.com"

        httpretty.register_uri(httpretty.POST, cherrypy.config["notifier.url"])

        body = {
            "siteName": "foo",
            "status": "success",
            "message": "line1 foo bar\nline2 foo bar \nline3 foo bar",
            "complete": True
        }

        requestMock.return_value = True

        response = self.request(path="/azure/test",
                                method="POST",
                                data=json.dumps(body).encode("utf-8"),
                                headers={"Content-type": "application/json"})

        args, kwargs = requestMock.call_args_list[0]
        notification = urllib.parse.parse_qs(kwargs["data"])
        self.assertEqual(notification[b"body"], [b"line1 foo bar"])

    def test_indexReturnsJson(self):
        """ The index returns json if requested """
        response = self.request("/", as_json=True)
        self.assertEqual(response.code, 200)
        self.assertTrue("endpoints" in response.body)

    def test_indexReturnsPlain(self):
        """ The index returns json if requested """
        response = self.request("/", as_plain=True)
        self.assertEqual(response.code, 200)
        self.assertTrue("/" in response.body)

    def test_ipNoToken(self):
        """ Calling /ip without a token should emit the caller's IP """
        headers = {
            "Remote-Addr": "1.1.1.1",
            "Authorization": "Basic dGVzdDp0ZXN0"
        }
        response = self.request("/ip", headers=headers)
        self.assertEqual(response.code, 200)
        self.assertTrue("1.1.1.1" in response.body)

    def test_ipNoTokenJson(self):
        """ The /ip endpoint returns json if requested """
        headers = {
            "Remote-Addr": "1.1.1.1",
            "Authorization": "Basic dGVzdDp0ZXN0",
            "Accept": "application/json"
        }
        response = self.request("/ip", headers=headers, as_json=True)
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body["address"], "1.1.1.1")

    def test_ipNoTokenPlain(self):
        """ The /ip endpoint returns plain text if requested """
        headers = {
            "Remote-Addr": "1.1.1.1",
            "Authorization": "Basic dGVzdDp0ZXN0"
        }
        response = self.request("/ip", headers=headers, as_plain=True)
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body, "1.1.1.1")

    def test_ipRightHeader(self):
        """ /ip should prefer X-Real-Ip header to Remote-Addr header """
        headers = {
            "Remote-Addr": "1.1.1.1",
            "X-REAL-IP": "2.2.2.2",
            "Authorization": "Basic dGVzdDp0ZXN0"
        }
        response = self.request("/ip", headers=headers)
        self.assertTrue("2.2.2.2" in response.body)

    def test_ipValidTokenHtml(self):
        """ /ip returns html by default when a valid token is provided """
        cherrypy.config["ip.dns.command"] = []
        headers = {
            "Remote-Addr": "1.1.1.1",
            "Authorization": "Basic dGVzdDp0ZXN0"
        }
        response = self.request("/ip/test", headers=headers)
        self.assertEqual(response.code, 200)
        self.assertTrue("<main" in response.body)

    def test_ipValidTokenJson(self):
        """ /ip returns json if requested when a valid token is provided """
        cherrypy.config["ip.dns.command"] = []
        headers = {
            "Remote-Addr": "1.1.1.1",
            "Authorization": "Basic dGVzdDp0ZXN0",
            "Accept": "application/json"
        }
        response = self.request("/ip/test", headers=headers)
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body["result"], "ok")

    def test_ipValidTokenPlain(self):
        """ /ip returns plain text if requested when a valid token is provided """
        cherrypy.config["ip.dns.command"] = []
        headers = {
            "Remote-Addr": "1.1.1.1",
            "X-REAL-IP": "2.2.2.2",
            "Authorization": "Basic dGVzdDp0ZXN0",
        }
        response = self.request("/ip/test", headers=headers, as_plain=True)
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body, "ok")

    def testipValidTokenUpdatesDns(self):
        """ /ip calls the configured DNS update command via subprocess if given a valid token """
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

        headers = {
            "Remote-Addr": remote_address,
            "Authorization": "Basic dGVzdDp0ZXN0"
        }
        with mock.patch("medley.subprocess") as subprocess:
            response = self.request("/ip/" + token, headers=headers)
            subprocess.call.assert_called_once_with(expected_command)

    def test_ipInvalidToken(self):
        """ /ip should fail if an invalid token is specified """
        headers = {
            "Remote-Addr": "1.1.1.1",
            "X-REAL-IP": "2.2.2.2",
            "Authorization": "Basic dGVzdDp0ZXN0"
        }
        response = self.request("/ip/invalid", headers=headers)
        self.assertEqual(response.code, 400)

    def test_ipInvalidTokenNoDns(self):
        """ /ip should not shell out if given an invalid token """
        headers = {
            "Remote-Addr": "1.1.1.1",
            "X-REAL-IP": "2.2.2.2",
            "Authorization": "Basic dGVzdDp0ZXN0"
        }
        with mock.patch("medley.subprocess") as subprocess:
            response = self.request("/ip/invalid", headers=headers)
            self.assertFalse(subprocess.called)

    def test_ipNoIp(self):
        """ /ip should fail if it can't identify the request ip """
        headers = {
            "Authorization": "Basic dGVzdDp0ZXN0"
        }
        response = self.request("/ip/test", headers=headers)
        self.assertEqual(response.code, 400)

    def test_headersReturnsHtml(self):
        """ The headers endpoint returns html by default """
        response = self.request("/headers")
        self.assertEqual(response.code, 200)
        self.assertTrue("<table" in response.body)

    def test_headersReturnsJson(self):
        """ The headers endpoint returns json if requested """
        response = self.request("/headers", as_json=True)
        self.assertEqual(response.code, 200)
        self.assertTrue("Accept" in response.body)

    def test_headersReturnsPlain(self):
        """ The headers endpoint returns plain text if requested """
        response = self.request("/headers", as_plain=True)
        self.assertEqual(response.code, 200)
        self.assertTrue("Accept" in response.body)

    def test_headersNoArgs(self):
        """ The headers endpoint does not take arguments """
        response = self.request("/headers/test")
        self.assertEqual(response.code, 404)

    def test_lettercaseReturnsHtml(self):
        """ The lettercase endpoint template includes a form by default """
        response = self.request("/lettercase")
        self.assertEqual(response.code, 200)
        self.assertTrue("<form" in response.body)

    def test_lettercaseReturnsJson(self):
        """ The lettercase endpoint returns json if requested """
        response = self.request("/lettercase", as_json=True)
        self.assertEqual(response.code, 200)
        self.assertTrue(response.body["result"] == "")

    def test_lettercaseConvertsToLowercase(self):
        """ The lettercase endpoint converts an input string to lowercase """
        response = self.request(path="/lettercase",
                                method="POST",
                                as_plain=True,
                                style="lower",
                                value="TEST")
        self.assertEqual(response.body, "test")

    def test_lettercaseConvertsToUppercase(self):
        """ The lettercase endpoint converts an input string to uppercase """
        response = self.request(path="/lettercase",
                                method="POST",
                                as_plain=True,
                                style="upper",
                                value="test")
        self.assertEqual(response.body, "TEST")

    def test_lettercaseConvertsToTitle(self):
        """ The lettercase endpoint converts an input string to title case """
        response = self.request(path="/lettercase",
                                method="POST",
                                as_plain=True,
                                style="title",
                                value="this iS a TEst 1999")
        self.assertEqual(response.body, "This Is A Test 1999")

    def test_geoupdateReturns410IfNoUrl(self):
        """ The geoupdate endpoint returns 410 if geoip.download.url is not configured """
        cherrypy.config["geoip.download.url"] = None
        cherrypy.config["database.directory"] = "/tmp"
        response = self.request("/geoupdate")
        self.assertEqual(response.code, 410)

    def test_geoupdateReturns410IfNoDatabaseDirectory(self):
        """ The geoupdate endpoint returns 410 if database.directory is not configured """
        cherrypy.config["geoip.download.url"] = "http://example.com/test.gz"
        cherrypy.config["database.directory"] = None
        response = self.request("/geoupdate")
        self.assertEqual(response.code, 410)

    @httpretty.activate
    def test_geoupdateReturns500IfGzipFails(self):
        """ The geoupdate endpoint returns 500 if the database cannot be gunzipped.
        Although we are mocking the download url, we're not getting back a gzipped file. """
        cherrypy.config["geoip.download.url"] = "http://example.com/test.gz"
        cherrypy.config["database.directory"] = "/tmp"
        httpretty.register_uri(httpretty.GET, cherrypy.config["geoip.download.url"])
        response = self.request("/geoupdate")
        self.assertEqual(response.code, 500)

    @httpretty.activate
    def test_geoupdateReturns200(self):
        """ The geoupdate endpoint returns 200 if the database is downloaded  """
        cherrypy.config["geoip.download.url"] = "http://example.com/test"
        cherrypy.config["database.directory"] = "/tmp"
        httpretty.register_uri(httpretty.GET, cherrypy.config["geoip.download.url"])
        response = self.request("/geoupdate")
        self.assertEqual(response.code, 200)

    @httpretty.activate
    def test_geoupdateReturns204(self):
        """ The geoupdate endpoint returns 204 when silent mode is requested  """
        cherrypy.config["geoip.download.url"] = "http://example.com/test"
        cherrypy.config["database.directory"] = "/tmp"
        httpretty.register_uri(httpretty.GET, cherrypy.config["geoip.download.url"])
        response = self.request("/geoupdate", silent=1)
        self.assertEqual(response.body, "")
        self.assertEqual(response.code, 204)

    def test_whoisJsonWithoutAddress(self):
        """ The /whois endpoint returns 400 if called as json without an address"""
        response = self.request("/whois", as_json=True)
        self.assertEqual(response.code, 400)
        self.assertTrue("message" in response.body)

    def test_whoisPlainWithoutAddress(self):
        """ The /whois endpoint returns 400 if called as plain without an address"""
        response = self.request("/whois", as_plain=True)
        self.assertEqual(response.code, 400)

    @mock.patch("util.net.whois")
    def test_whoisGeoipQuery(self, queryWhoisMock):
        """ The /whois endpoint calls the geoip database """
        reader = mock.MagicMock()
        reader.record_by_addr.return_value = {}
        queryWhoisMock.return_value = {}
        ip = "1.1.1.1"
        with mock.patch("medley.pygeoip.GeoIP") as pygeoip_mock:
            pygeoip_mock.return_value = reader
            response = self.request("/whois/" + ip, as_json=True)
            reader.record_by_addr.assert_called_once_with(ip)
            queryWhoisMock.assert_called_once_with(ip)

    @mock.patch("util.net.whois")
    def test_whoisPopulateUsMapParams(self, queryWhoisMock):
        """ The /whois endpoint defines the map region for a US IP as US-{state abbrev} """
        reader = mock.MagicMock()
        reader.record_by_addr.return_value = {
            "country_code": "US",
            "region_code": "NY"
        }
        queryWhoisMock.return_value = {}
        with mock.patch("medley.pygeoip") as pygeoip_mock:
            pygeoip_mock.GeoIP.return_value = reader
            response = self.request("/whois/1.1.1.1", as_json=True)
            self.assertEqual(response.body["map_region"], "US-NY")

    @mock.patch("util.net.whois")
    def test_whoisPopulateNonUsMapParams(self, queryWhoisMock):
        """ The /whois endpoint defines the map region for a non-US IP as a 2-letter ISO code """
        reader = mock.MagicMock()
        reader.record_by_addr.return_value = {
            "country_code": "AU"
        }
        queryWhoisMock.return_value = {}
        with mock.patch("medley.pygeoip") as pygeoip_mock:
            pygeoip_mock.GeoIP.return_value = reader
            response = self.request("/whois/1.1.1.1", as_json=True)
            self.assertEqual(response.body["map_region"], "AU")

    @mock.patch("util.net.whois")
    def test_whoisSkipsGeoipQuery(self, queryWhoisMock):
        """ The /whois endpoint returns if the geoip query fails """
        queryWhoisMock.return_value = {}
        with mock.patch("medley.pygeoip") as pygeoip_mock:
            pygeoip_mock.GeoIP = mock.MagicMock(side_effect=Exception('Force fail'))
            response = self.request("/whois/1.1.1.1", as_json=True)
            self.assertTrue(response.code, 200)

    @mock.patch("util.net.whois")
    def test_whoisPlainReturnsCityAndCountry(self, queryWhoisMock):
        """ The /whois endpoint returns if the geoip query fails """
        reader = mock.MagicMock()
        reader.record_by_addr.return_value = {
            "city": "test city",
            "country_code": "AA",
            "region_code": "BB",
            "country_name": "test country"
        }
        queryWhoisMock.return_value = {}

        with mock.patch("medley.pygeoip") as pygeoip_mock:
            pygeoip_mock.GeoIP.return_value = reader
            response = self.request("/whois/1.1.1.1", as_plain=True)
            self.assertEqual(response.body, "test city, test country")

    @mock.patch("util.net.whois")
    def test_whoisPlainReturnsCountry(self, queryWhoisMock):
        """ The /whois endpoint returns if the geoip query fails """
        reader = mock.MagicMock()
        reader.record_by_addr.return_value = {
            "country_code": "AA",
            "region_code": "BB",
            "country_name": "test country"
        }
        queryWhoisMock.return_value = {}

        with mock.patch("medley.pygeoip") as pygeoip_mock:
            pygeoip_mock.GeoIP.return_value = reader
            response = self.request("/whois/1.1.1.1", as_plain=True)
            self.assertEqual(response.body, "test country")

    @mock.patch("util.net.whois")
    def test_whoisPlainReturnsUnknown(self, queryWhoisMock):
        """ The /whois endpoint returns if the geoip query fails """
        reader = mock.MagicMock()
        reader.record_by_addr.return_value = {}
        queryWhoisMock.return_value = {}

        with mock.patch("medley.pygeoip") as pygeoip_mock:
            pygeoip_mock.GeoIP.return_value = reader
            response = self.request("/whois/1.1.1.1", as_plain=True)
            self.assertEqual(response.body, "Unknown")

    @mock.patch("util.net.whois")
    def test_whoisInputIp(self, queryWhoisMock):
        """ The /whois endpoint accepts an IP address as input """
        queryWhoisMock.return_value = {}
        with mock.patch("medley.pygeoip") as pygeoip_mock:
            pygeoip_mock.GeoIP = mock.MagicMock(side_effect=Exception('Force fail'))
            response = self.request("/whois/1.1.1.1", as_json=True)
            self.assertEqual(response.body["ip"], "1.1.1.1")

    @mock.patch("util.net.resolveHost")
    @mock.patch("util.net.whois")
    def test_whoisInputHostname(self, whoisMock, resolveHostMock):
        """ The /whois endpoint accepts a hostname as input """
        whoisMock.return_value = {}
        resolveHostMock.return_value = "1.1.1.1"
        with mock.patch("medley.pygeoip") as pygeoip_mock:
            pygeoip_mock.GeoIP = mock.MagicMock(side_effect=Exception('Force fail'))
            response = self.request("/whois/example.com", as_json=True)
            self.assertEqual(response.body["ip"], "1.1.1.1")

    @mock.patch("util.net.resolveHost")
    @mock.patch("util.net.whois")
    def test_whoisInputUrl(self, whoisMock, resolveHostMock):
        """ The /whois endpoint accepts a full URL as input """
        whoisMock.return_value = {}
        resolveHostMock.return_value = "1.1.1.1"
        with mock.patch("medley.pygeoip") as pygeoip_mock:
            pygeoip_mock.GeoIP = mock.MagicMock(side_effect=Exception('Force fail'))
            address = urllib.parse.quote_plus("http://example.com/foo/bar?a=1")
            response = self.request("/whois/" + address, as_json=True)
            self.assertEqual(response.body["ip"], "1.1.1.1")
            self.assertEqual(response.body["address"], "example.com")

    @mock.patch("util.net.resolveHost")
    @mock.patch("util.net.whois")
    def test_whoisInputHostAlias(self, whoisMock, resolveHostMock):
        """ The /whois endpoint accepts a full URL as input """
        whoisMock.return_value = {}
        resolveHostMock.return_value = "1.1.1.1"
        with mock.patch("medley.pygeoip") as pygeoip_mock:
            pygeoip_mock.GeoIP = mock.MagicMock(side_effect=Exception('Force fail'))
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

    @mock.patch("medley.util.phone.callHistory")
    @httpretty.activate
    def test_phoneValidAreaCodeJson(self, callHistory):
        """The /phone queries dbpedia twice and returns the state name for the
        given area code as a json object if requested as json"""

        area_code_response = helpers.getFixture("dbpedia-area-success.json")
        state_name_response = helpers.getFixture("dbpedia-state-success.json")
        callHistory.return_value = ([], 0)

        httpretty.register_uri(httpretty.GET,
                               "http://dbpedia.org/sparql",
                               responses=[
                                   httpretty.Response(body=area_code_response, status=200),
                                   httpretty.Response(body=state_name_response, status=200)
                               ])

        response = self.request("/phone/212", as_json=True)
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body["state_name"], "New York")

    @mock.patch("medley.util.phone.callHistory")
    @httpretty.activate
    def test_phoneValidAreaCodePlain(self, callHistory):
        """/phone queries dbpedia twice and sets the request body to the state
        name if requsted as plain"""

        area_code_response = helpers.getFixture("dbpedia-area-success.json")
        state_name_response = helpers.getFixture("dbpedia-state-success.json")
        callHistory.return_value = ([], 0)

        httpretty.register_uri(httpretty.GET,
                               "http://dbpedia.org/sparql",
                               responses=[
                                   httpretty.Response(body=area_code_response, status=200),
                                   httpretty.Response(body=state_name_response, status=200)
                               ])

        response = self.request("/phone/212", as_plain=True)
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body, "New York")

    @mock.patch("medley.util.phone.callHistory")
    @httpretty.activate
    def test_phoneInvalidAreaCodeJson(self, callHistory):
        """The /phone endpoint queries dbpedia once if the specified area code
        is invalid"""

        area_code_response = helpers.getFixture("dbpedia-area-fail.json")
        callHistory.return_value = ([], 0)

        httpretty.register_uri(httpretty.GET,
                               "http://dbpedia.org/sparql",
                               body=area_code_response,
                               content_type="application/json")

        response = self.request("/phone/123", as_json=True)
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body["state_abbreviation"], None)

    @mock.patch("medley.util.phone.callHistory")
    @httpretty.activate
    def test_phoneInvalidAreaCodePlain(self, callHistory):
        """The /phone endpoint returns "Unknown" for an invalid area code when
        requested as plain"""

        area_code_response = helpers.getFixture("dbpedia-area-fail.json")
        callHistory.return_value = ([], 0)

        httpretty.register_uri(httpretty.GET,
                               "http://dbpedia.org/sparql",
                               body=area_code_response,
                               content_type="application/json")

        response = self.request("/phone/123", as_plain=True)
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body, "Unknown")

    @mock.patch("medley.util.phone.callHistory")
    @httpretty.activate
    def test_phoneAreaCodeFail(self, callHistory):
        """The /phone endpoint returns successfully if the dbpedia area code
        query fails"""

        callHistory.return_value = ([], 0)
        httpretty.register_uri(httpretty.GET,
                               "http://dbpedia.org/sparql",
                               status=500)

        response = self.request("/phone/123")
        self.assertEqual(response.code, 200)

    @mock.patch("medley.util.net.externalIp")
    def test_externalIpSuccessPlain(self, externalIp):
        """The /external-ip endpoint returns an IP address when the
        DNS-O-Matic query succeeds"""
        cherrypy.request.app.config["ip_tokens"]["external"] = "external.example.com"
        address = "1.1.1.1"
        externalIp.return_value = address

        response = self.request("/external-ip", as_plain=True)
        self.assertEqual(response.body, address)

    @mock.patch("medley.util.net.externalIp")
    def test_externalIpSuccessJson(self, externalIp):
        """The /external-ip endpoint returns an IP address when the
        DNS-O-Matic query succeeds"""
        cherrypy.request.app.config["ip_tokens"]["external"] = "external.example.com"
        address = "1.1.1.1"
        externalIp.return_value = address

        response = self.request("/external-ip", as_json=True)
        self.assertEqual(response.body["ip"], address)

    @mock.patch("medley.util.net.externalIp")
    def test_externalIpSuccessSilent(self, externalIp):
        """The /external-ip endpoint returns 204 when silent mode is requested"""
        cherrypy.request.app.config["ip_tokens"]["external"] = "external.example.com"
        address = "1.1.1.1"
        externalIp.return_value = address

        response = self.request("/external-ip", silent=1)
        self.assertEqual(response.body, "")
        self.assertEqual(response.code, 204)


    @mock.patch("medley.util.net.externalIp")
    def test_externalIpFail(self, externalIp):
        """The /external-ip endpoint returns the string "not available" when the
        DNS-O-Matic query fails"""
        cherrypy.request.app.config["ip_tokens"]["external"] = "external.example.com"
        externalIp.return_value = None

        response = self.request("/external-ip", as_plain=True)
        self.assertEqual(response.body, "not available")

    @mock.patch("medley.util.net.externalIp")
    def test_externalIpNoHost(self, externalIp):
        """The /external-ip endpoint returns 500 if an external hostname has not been defined"""
        cherrypy.request.app.config["ip_tokens"]["external"] = None
        externalIp.return_value = None

        response = self.request("/external-ip", as_plain=True)
        self.assertEqual(response.code, 500)

    @mock.patch("medley.util.net.externalIp")
    def test_externalIpUpdatesDns(self, externalIp):
        """The /external-ip endpoint updates the local DNS server, setting the
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
        """The /dnsmatch endpoint requires a URL token to determine which
        hosts to check."""
        response = self.request("/dnsmatch")
        self.assertEqual(response.code, 400)

    def test_dnsmatchInvalidToken(self):
        """The /dnsmatch endpoint rejects URL tokens that are not in the config."""
        response = self.request("/dnsmatch/foo")
        self.assertEqual(response.code, 400)

    def test_dnsmatchOk(self):
        """ If there is no mismatch, /dnsmatch returns a result of ok"""
        with mock.patch("medley.subprocess.Popen") as popen:
            popen.return_value.communicate.side_effect = [(b"foo", None), (b"foo", None)]
            response = self.request("/dnsmatch/test", as_json=True)
            self.assertTrue("result" in response.body)
            self.assertTrue("commands" in response.body)
            self.assertTrue("command_results" in response.body)
            self.assertEqual(response.body["result"], "ok")

    def test_dnsmatchSilent(self):
        """ In silent mode, /dnsmatch returns 204"""
        with mock.patch("medley.subprocess.Popen") as popen:
            popen.return_value.communicate.side_effect = [(b"foo", None), (b"foo", None)]
            response = self.request("/dnsmatch/test", silent=1)
            self.assertEqual(response.body, "")
            self.assertEqual(response.code, 204)

    def test_dnsmatchOkPlain(self):
        """ If there is no mismatch, /dnsmatch returns a result of ok"""
        with mock.patch("medley.subprocess.Popen") as popen:
            popen.return_value.communicate.side_effect = [(b"foo", None), (b"foo", None)]
            response = self.request("/dnsmatch/test", as_plain=True)
            self.assertEqual(response.body, "ok")

    def test_dnsmatchMismatch(self):
        """ If there is no mismatch, /dnsmatch returns a result of mismatch"""
        with mock.patch("medley.subprocess.Popen") as popen:
            popen.return_value.communicate.side_effect = [(b"foo", None), (b"bar", None)]
            response = self.request("/dnsmatch/test", as_json=True)
            self.assertTrue("result" in response.body)
            self.assertTrue("commands" in response.body)
            self.assertTrue("command_results" in response.body)
            self.assertEqual(response.body["result"], "mismatch")

    @mock.patch("util.net.sendMessage")
    def test_dnsmatchEmailOnlyOnPost(self, sendMessage):
        """ Email is only sent on post requsts."""
        with mock.patch("medley.subprocess.Popen") as popen:
            popen.return_value.communicate.side_effect = [(b"foo", None), (b"bar", None)]
            response = self.request("/dnsmatch/test", as_json=True)
            self.assertFalse(sendMessage.called)

    @mock.patch("util.net.sendMessage")
    def test_dnsmatchSendEmail(self, sendMessage):
        """ Email is only sent on post requsts."""
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
