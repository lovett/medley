import cptestcase
import helpers
import unittest
import responses
import apps.whois.main
import mock
import util.db
import time
import socket

class TestWhois(cptestcase.BaseCherryPyTestCase):
    @classmethod
    def setUpClass(cls):
        helpers.start_server(apps.whois.main.Controller)

    @classmethod
    def tearDownClass(cls):
        helpers.stop_server()

    def test_jsonRequiresAddress(self):
        """Returns 400 if called as json without an address"""
        response = self.request("/", as_json=True)
        self.assertEqual(response.code, 400)
        self.assertTrue("message" in response.body)

    def test_textRequiresAddress(self):
        """Returns 400 if called as text without an address"""
        response = self.request("/", as_plain=True)
        self.assertEqual(response.code, 400)

    def test_htmlDoesNotRequireAddress(self):
        """Returns HTML search form if no address is specified"""
        response = self.request("/")
        self.assertEqual(response.code, 200)
        self.assertTrue("<main" in response.body)
        self.assertTrue("<form" in response.body)

    @mock.patch("util.db.ipFacts")
    @mock.patch("util.db.cacheSet")
    @mock.patch("util.db.cacheGet")
    def test_addressAsIp(self, cacheGetMock, cacheSetMock, ipFactsMock):
        """Accepts IP addresses"""
        cacheGetMock.return_value = ({},)
        ipFactsMock.return_value = {}
        response = self.request("/", address="1.1.1.1", as_json=True)
        self.assertTrue(cacheGetMock.called)
        self.assertFalse(cacheSetMock.called)
        self.assertTrue(ipFactsMock.called)

    @mock.patch("apps.whois.main.Controller.resolveHost")
    @mock.patch("util.db.ipFacts")
    @mock.patch("util.db.cacheSet")
    @mock.patch("util.db.cacheGet")
    def test_addressAsHostname(self, cacheGetMock, cacheSetMock, ipFactsMock, resolveHostMock):
        """Accepts hostnames"""
        cacheGetMock.return_value = ({},)
        ipFactsMock.return_value = {}
        resolveHostMock.return_value = "1.1.1.1"
        response = self.request("/", address="example.com", as_json=True)
        self.assertEqual(response.body["ip"], "1.1.1.1")
        self.assertTrue(cacheGetMock.called)
        self.assertFalse(cacheSetMock.called)
        self.assertTrue(ipFactsMock.called)

    @mock.patch("apps.whois.main.Controller.resolveHost")
    @mock.patch("util.db.ipFacts")
    @mock.patch("util.db.cacheSet")
    @mock.patch("util.db.cacheGet")
    def test_addressAsUrl(self, cacheGetMock, cacheSetMock, ipFactsMock, resolveHostMock):
        """Accepts hostnames expressed as URLs"""
        cacheGetMock.return_value = ({},)
        ipFactsMock.return_value = {}
        resolveHostMock.return_value = "1.1.1.1"
        response = self.request("/", address="http://www.example.com", as_json=True)
        self.assertEqual(response.body["ip"], "1.1.1.1")
        self.assertTrue(cacheGetMock.called)
        self.assertFalse(cacheSetMock.called)
        self.assertTrue(ipFactsMock.called)

    @mock.patch("apps.whois.main.Controller.resolveHost")
    @mock.patch("util.db.ipFacts")
    @mock.patch("util.db.cacheSet")
    @mock.patch("util.db.cacheGet")
    def test_addressAsInvalidHostnameJson(self, cacheGetMock, cacheSetMock, ipFactsMock, resolveHostMock):
        """Rejects an address that cannot be resolved to an IP"""
        cacheGetMock.return_value = ({},)
        ipFactsMock.return_value = {}
        resolveHostMock.return_value = None
        response = self.request("/", address="not-a-valid-hostname", as_json=True)
        self.assertTrue(response.code, 400)
        self.assertFalse(cacheGetMock.called)
        self.assertFalse(cacheSetMock.called)
        self.assertFalse(ipFactsMock.called)
        self.assertTrue("message" in response.body)

        response = self.request("/", address="not-a-valid-hostname2", as_plain=True)
        self.assertTrue(response.code, 401)

    @responses.activate
    @mock.patch("util.db.ipFacts")
    @mock.patch("util.db.cacheSet")
    @mock.patch("util.db.cacheGet")
    def test_cachesArinLookup(self, cacheGetMock, cacheSetMock, ipFactsMock):
        """Accepts IP addresses"""
        cacheGetMock.return_value = ({"foo": "bar"},)
        ipFactsMock.return_value = {}
        response = self.request("/", address="1.1.1.1", as_json=True)
        self.assertTrue(cacheGetMock.called)
        self.assertFalse(cacheSetMock.called)
        self.assertTrue(ipFactsMock.called)
        self.assertEqual(len(responses.calls), 0)

    @responses.activate
    @mock.patch("util.db.ipFacts")
    @mock.patch("util.db.cacheSet")
    @mock.patch("util.db.cacheGet")
    def test_queriesArin(self, cacheGetMock, cacheSetMock, ipFactsMock):
        """Queries whois.arin.net if a cached value is not found"""
        cacheGetMock.return_value = None
        ipFactsMock.return_value = {}
        responses.add(responses.GET, "http://whois.arin.net/rest/ip/1.1.1.1", body='{"foo":"bar"}')
        response = self.request("/", address="1.1.1.1", as_json=True)
        self.assertEqual(response.code, 200)
        self.assertTrue(cacheGetMock.called)
        self.assertTrue(cacheSetMock.called)
        self.assertTrue(ipFactsMock.called)
        self.assertEqual(len(responses.calls), 1)

    @mock.patch("util.db.ipFacts")
    @mock.patch("util.db.cacheGet")
    def test_mapRegionUs(self, cacheGetMock, ipFactsMock):
        """ Defines the map region for a US IP as US-{state abbrev} """
        cacheGetMock.return_value = ({"foo": "bar"},)
        ipFactsMock.return_value = {
            "geo": {
                "country_code": "US",
                "region_code": "NY"
            }
        }
        response = self.request("/", address="1.1.1.1", as_json=True)
        self.assertEqual(response.body["map_region"], "US-NY")

    @mock.patch("util.db.ipFacts")
    @mock.patch("util.db.cacheGet")
    def test_mapRegionUsWithoutRegionCode(self, cacheGetMock, ipFactsMock):
        """Defines the map region for a US IP as US-{state abbrev} """
        cacheGetMock.return_value = ({"foo": "bar"},)
        ipFactsMock.return_value = {
            "geo": {
                "country_code": "US"
            }
        }
        response = self.request("/", address="1.1.1.1", as_json=True)
        self.assertEqual(response.body["map_region"], "US")

    @mock.patch("util.db.ipFacts")
    @mock.patch("util.db.cacheGet")
    def test_textResponseCityAndCountry(self, cacheGetMock, ipFactsMock):
        """Returns city and country as text if both are available"""
        cacheGetMock.return_value = ({"foo": "bar"},)
        ipFactsMock.return_value = {
            "geo": {
                "city": "test city",
                "country_name": "test country"
            }
        }
        response = self.request("/", address="1.1.1.1", as_plain=True)
        self.assertEqual(response.body, "test city, test country")

    @mock.patch("util.db.ipFacts")
    @mock.patch("util.db.cacheGet")
    def test_textResponseCountry(self, cacheGetMock, ipFactsMock):
        """Returns the country as text if a city is not available"""
        cacheGetMock.return_value = ({"foo": "bar"},)
        ipFactsMock.return_value = {
            "geo": {
                "country_name": "test country"
            }
        }
        response = self.request("/", address="1.1.1.1", as_plain=True)
        self.assertEqual(response.body, "test country")

    @mock.patch("util.db.ipFacts")
    @mock.patch("util.db.cacheGet")
    def test_textResponseUnknown(self, cacheGetMock, ipFactsMock):
        """Returns the string Unknown if the geolocation cannot be determined"""
        cacheGetMock.return_value = ({"foo": "bar"},)
        ipFactsMock.return_value = {
            "geo": {}
        }
        response = self.request("/", address="1.1.1.1", as_plain=True)
        self.assertTrue(response.code, 200)
        self.assertEqual(response.body, "Unknown")


    @mock.patch("util.db.ipFacts")
    @mock.patch("util.db.cacheGet")
    def test_whoisPopulateNonUsMapParams(self, cacheGetMock, ipFactsMock):
        """Defines the map region for a non-US IP as a 2-letter ISO code """
        cacheGetMock.return_value = ({"foo": "bar"},)
        ipFactsMock.return_value = {
            "geo": {
                "country_code": "AU"
            }
        }
        response = self.request("/", address="1.1.1.1", as_json=True)
        self.assertEqual(response.body["map_region"], "AU")

    @mock.patch("socket.gethostbyaddr")
    @mock.patch("util.db.ipFacts")
    @mock.patch("util.db.cacheGet")
    def test_reverseLookup(self, cacheGetMock, ipFactsMock, getHostMock):
        """Performs a reverse IP lookup"""
        cacheGetMock.return_value = ({"foo": "bar"},)
        ipFactsMock.return_value = {}
        getHostMock.return_value = ("example.com", [], [])
        response = self.request("/", address="1.1.1.1", as_json=True)

        self.assertEqual(response.body["reverse_host"], "example.com")
        self.assertTrue(getHostMock.called)

    @mock.patch("socket.gethostbyname_ex")
    @mock.patch("util.db.ipFacts")
    @mock.patch("util.db.cacheGet")
    def test_hostToIp(self, cacheGetMock, ipFactsMock, getHostMock):
        """Converts a hostname to an IP"""
        cacheGetMock.return_value = ({"foo": "bar"},)
        ipFactsMock.return_value = {}
        getHostMock.return_value = ("example.com", [], ["1.1.1.1"])
        response = self.request("/", address="example.com", as_json=True)

        self.assertEqual(response.body["ip"], "1.1.1.1")
        self.assertTrue(getHostMock.called)

    @mock.patch("socket.gethostbyname_ex")
    @mock.patch("util.db.ipFacts")
    @mock.patch("util.db.cacheGet")
    def test_hostToIpException(self, cacheGetMock, ipFactsMock, getHostMock):
        """Handles exceptions from hostname to IP conversion"""
        cacheGetMock.return_value = ({"foo": "bar"},)
        ipFactsMock.return_value = {}
        getHostMock.side_effect = Exception()
        response = self.request("/", address="example.com", as_json=True)

        self.assertEqual(response.code, 400)
        self.assertTrue(getHostMock.called)

if __name__ == "__main__":
    unittest.main()
