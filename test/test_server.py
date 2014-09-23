import cherrypy
import os.path
import json
import httpretty
import helpers
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
        },
        "/ip": {
            "tools.auth_basic.checkpassword": cherrypy.lib.auth_basic.checkpassword_dict({
                "test":"test"
            })
        },
        "ip_tokens": {
            "test": "test.example.com"
        }
    }

    app.merge(config_extra)

    cherrypy.engine.start()

def teardown_module():
    cherrypy.engine.exit()

class TestMedleyServer(BaseCherryPyTestCase):
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
        headers = {
            "Remote-Addr": "1.1.1.1",
            "Authorization": "Basic dGVzdDp0ZXN0"
        }
        response = self.request("/ip/test", headers=headers)
        self.assertEqual(response.code, 200)
        self.assertTrue("<main" in response.body)

    def test_ipValidTokenJson(self):
        """ /ip returns json if requested when a valid token is provided """
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
        kwargs = {
            "style": "lower",
            "value": "TEST"
        }
        response = self.request(path="/lettercase",
                                method="POST",
                                as_plain=True,
                                **kwargs)
        self.assertEqual(response.body, "test")

    def test_lettercaseConvertsToUppercase(self):
        """ The lettercase endpoint converts an input string to uppercase """
        kwargs = {
            "style": "upper",
            "value": "test"
        }
        response = self.request(path="/lettercase",
                                method="POST",
                                as_plain=True,
                                **kwargs)
        self.assertEqual(response.body, "TEST")

    def test_lettercaseConvertsToTitle(self):
        """ The lettercase endpoint converts an input string to title case """
        kwargs = {
            "style": "title",
            "value": "this iS a TEst 1999"
        }
        response = self.request(path="/lettercase",
                                method="POST",
                                as_plain=True,
                                **kwargs)
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

    def test_whoisJsonWithoutIp(self):
        """ The /whois endpoint returns 400 if called as json without an IP"""
        response = self.request("/whois", as_json=True)
        self.assertEqual(response.code, 400)
        self.assertTrue("message" in response.body)

    def test_whoisPlainWithoutIp(self):
        """ The /whois endpoint returns 400 if called as plain without an IP"""
        response = self.request("/whois", as_plain=True)
        self.assertEqual(response.code, 400)

    @mock.patch("util.whois.query")
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

    @mock.patch("util.whois.query")
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

    @mock.patch("util.whois.query")
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

    @mock.patch("util.whois.query")
    def test_whoisSkipsGeoipQuery(self, queryWhoisMock):
        """ The /whois endpoint returns if the geoip query fails """
        queryWhoisMock.return_value = {}
        with mock.patch("medley.pygeoip") as pygeoip_mock:
            pygeoip_mock.GeoIP = mock.MagicMock(side_effect=Exception('Force fail'))
            response = self.request("/whois/1.1.1.1", as_json=True)
            self.assertTrue(response.code, 200)

    @mock.patch("util.whois.query")
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

    @mock.patch("util.whois.query")
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

    @mock.patch("util.whois.query")
    def test_whoisPlainReturnsUnknown(self, queryWhoisMock):
        """ The /whois endpoint returns if the geoip query fails """
        reader = mock.MagicMock()
        reader.record_by_addr.return_value = {}
        queryWhoisMock.return_value = {}

        with mock.patch("medley.pygeoip") as pygeoip_mock:
            pygeoip_mock.GeoIP.return_value = reader
            response = self.request("/whois/1.1.1.1", as_plain=True)
            self.assertEqual(response.body, "Unknown")

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

    @httpretty.activate
    def test_phoneValidAreaCodeJson(self):
        """The /phone queries dbpedia twice and returns the state name for the
        given area code as a json object if requested as json"""

        area_code_response = helpers.getFixture("dbpedia-area-success.json")
        state_name_response = helpers.getFixture("dbpedia-state-success.json")

        httpretty.register_uri(httpretty.GET,
                               "http://dbpedia.org/sparql",
                               responses=[
                                   httpretty.Response(body=area_code_response, status=200),
                                   httpretty.Response(body=state_name_response, status=200)
                               ])

        response = self.request("/phone/212", as_json=True)
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body["state_name"], "New York")

    @httpretty.activate
    def test_phoneValidAreaCodePlain(self):
        """/phone queries dbpedia twice and sets the request body to the state
        name if requsted as plain"""

        area_code_response = helpers.getFixture("dbpedia-area-success.json")
        state_name_response = helpers.getFixture("dbpedia-state-success.json")

        httpretty.register_uri(httpretty.GET,
                               "http://dbpedia.org/sparql",
                               responses=[
                                   httpretty.Response(body=area_code_response, status=200),
                                   httpretty.Response(body=state_name_response, status=200)
                               ])

        response = self.request("/phone/212", as_plain=True)
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body, "New York")

    @httpretty.activate
    def test_phoneInvalidAreaCodeJson(self):
        """The /phone endpoint queries dbpedia once if the specified area code
        is invalid"""

        area_code_response = helpers.getFixture("dbpedia-area-fail.json")

        httpretty.register_uri(httpretty.GET,
                               "http://dbpedia.org/sparql",
                               body=area_code_response,
                               content_type="application/json")

        response = self.request("/phone/123", as_json=True)
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body["state_abbreviation"], None)

    @httpretty.activate
    def test_phoneInvalidAreaCodePlain(self):
        """The /phone endpoint returns "Unknown" for an invalid area code when
        requested as plain"""

        area_code_response = helpers.getFixture("dbpedia-area-fail.json")

        httpretty.register_uri(httpretty.GET,
                               "http://dbpedia.org/sparql",
                               body=area_code_response,
                               content_type="application/json")

        response = self.request("/phone/123", as_plain=True)
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body, "Unknown")

    @httpretty.activate
    def test_phoneAreaCodeFail(self):
        """The /phone endpoint returns successfully if the dbpedia area code
        query fails"""

        httpretty.register_uri(httpretty.GET,
                               "http://dbpedia.org/sparql",
                               status=500)

        response = self.request("/phone/123")
        self.assertEqual(response.code, 200)


if __name__ == "__main__":
    import unittest
    unittest.main()
