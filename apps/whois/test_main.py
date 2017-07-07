from testing import cptestcase
from testing import helpers
import unittest
import responses
import apps.whois.main
import mock
import util.cache
import util.ip
import time
import socket
import shutil
import tempfile
import cherrypy

class TestWhois(cptestcase.BaseCherryPyTestCase):
    @classmethod
    def setUpClass(cls):
        helpers.start_server(apps.whois.main.Controller)

    @classmethod
    def tearDownClass(cls):
        helpers.stop_server()

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="awsranges-test")
        cherrypy.config["database_dir"] = self.temp_dir

    def tearDown(self):
        shutil.rmtree(self.temp_dir)


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

    @mock.patch("util.ip.facts")
    @mock.patch("util.cache.Cache.set")
    @mock.patch("util.cache.Cache.get")
    def test_addressAsIp(self, cacheGetMock, cacheSetMock, factsMock):
        """Accepts IP addresses"""
        cacheGetMock.return_value = ({},)
        factsMock.return_value = {}
        response = self.request("/", address="1.1.1.1", as_json=True)
        self.assertTrue(cacheGetMock.called)
        self.assertFalse(cacheSetMock.called)
        self.assertTrue(factsMock.called)

    @mock.patch("apps.whois.main.Controller.resolveHost")
    @mock.patch("util.ip.facts")
    @mock.patch("util.cache.Cache.set")
    @mock.patch("util.cache.Cache.get")
    def test_addressAsHostname(self, cacheGetMock, cacheSetMock, factsMock, resolveHostMock):
        """Accepts hostnames"""
        cacheGetMock.return_value = ({},)
        factsMock.return_value = {}
        resolveHostMock.return_value = "1.1.1.1"
        response = self.request("/", address="example.com", as_json=True)
        self.assertEqual(response.body["ip"], "1.1.1.1")
        self.assertTrue(cacheGetMock.called)
        self.assertFalse(cacheSetMock.called)
        self.assertTrue(factsMock.called)

    @mock.patch("apps.whois.main.Controller.resolveHost")
    @mock.patch("util.ip.facts")
    @mock.patch("util.cache.Cache.set")
    @mock.patch("util.cache.Cache.get")
    def test_addressAsUrl(self, cacheGetMock, cacheSetMock, factsMock, resolveHostMock):
        """Accepts hostnames expressed as URLs"""
        cacheGetMock.return_value = ({},)
        factsMock.return_value = {}
        resolveHostMock.return_value = "1.1.1.1"
        response = self.request("/", address="http://www.example.com", as_json=True)
        self.assertEqual(response.body["ip"], "1.1.1.1")
        self.assertTrue(cacheGetMock.called)
        self.assertFalse(cacheSetMock.called)
        self.assertTrue(factsMock.called)

    @mock.patch("apps.whois.main.Controller.resolveHost")
    @mock.patch("util.ip.facts")
    @mock.patch("util.cache.Cache.set")
    @mock.patch("util.cache.Cache.get")
    def test_addressAsInvalidHostnameJson(self, cacheGetMock, cacheSetMock, factsMock, resolveHostMock):
        """Rejects an address that cannot be resolved to an IP"""
        cacheGetMock.return_value = ({},)
        factsMock.return_value = {}
        resolveHostMock.return_value = None
        response = self.request("/", address="not-a-valid-hostname", as_json=True)
        self.assertTrue(response.code, 400)
        self.assertFalse(cacheGetMock.called)
        self.assertFalse(cacheSetMock.called)
        self.assertFalse(factsMock.called)
        self.assertTrue("message" in response.body)

        response = self.request("/", address="not-a-valid-hostname2", as_plain=True)
        self.assertTrue(response.code, 401)

    @responses.activate
    @mock.patch("util.ip.facts")
    @mock.patch("util.cache.Cache.set")
    @mock.patch("util.cache.Cache.get")
    def test_cachesArinLookup(self, cacheGetMock, cacheSetMock, factsMock):
        """Accepts IP addresses"""
        cacheGetMock.return_value = ({"foo": "bar"},)
        factsMock.return_value = {}
        response = self.request("/", address="1.1.1.1", as_json=True)
        self.assertTrue(cacheGetMock.called)
        self.assertFalse(cacheSetMock.called)
        self.assertTrue(factsMock.called)
        self.assertEqual(len(responses.calls), 0)

    @responses.activate
    @mock.patch("util.ip.facts")
    @mock.patch("util.cache.Cache.set")
    @mock.patch("util.cache.Cache.get")
    def test_queriesArin(self, cacheGetMock, cacheSetMock, factsMock):
        """Queries whois.arin.net if a cached value is not found"""
        cacheGetMock.return_value = None
        factsMock.return_value = {}
        responses.add(responses.GET, "http://whois.arin.net/rest/ip/1.1.1.1", body='{"foo":"bar"}')
        response = self.request("/", address="1.1.1.1", as_json=True)
        self.assertEqual(response.code, 200)
        self.assertTrue(cacheGetMock.called)
        self.assertTrue(cacheSetMock.called)
        self.assertTrue(factsMock.called)
        self.assertEqual(len(responses.calls), 1)

    @mock.patch("util.ip.facts")
    @mock.patch("util.cache.Cache.get")
    def test_mapRegionUs(self, cacheGetMock, factsMock):
        """ Defines the map region for a US IP as US-{state abbrev} """
        cacheGetMock.return_value = ({"foo": "bar"},)
        factsMock.return_value = {
            "geo": {
                "country_code": "US",
                "region_code": "NY"
            }
        }
        response = self.request("/", address="1.1.1.1", as_json=True)
        self.assertEqual(response.body["map_region"], "US-NY")

    @mock.patch("util.ip.facts")
    @mock.patch("util.cache.Cache.get")
    def test_mapRegionUsWithoutRegionCode(self, cacheGetMock, factsMock):
        """Defines the map region for a US IP as US-{state abbrev} """
        cacheGetMock.return_value = ({"foo": "bar"},)
        factsMock.return_value = {
            "geo": {
                "country_code": "US"
            }
        }
        response = self.request("/", address="1.1.1.1", as_json=True)
        self.assertEqual(response.body["map_region"], "US")

    @mock.patch("util.ip.facts")
    @mock.patch("util.cache.Cache.get")
    def test_textResponseCityAndCountry(self, cacheGetMock, factsMock):
        """Returns city and country as text if both are available"""
        cacheGetMock.return_value = ({"foo": "bar"},)
        factsMock.return_value = {
            "geo": {
                "city": "test city",
                "country_name": "test country"
            }
        }
        response = self.request("/", address="1.1.1.1", as_plain=True)
        self.assertEqual(response.body, "test city, test country")

    @mock.patch("util.ip.facts")
    @mock.patch("util.cache.Cache.get")
    def test_textResponseCountry(self, cacheGetMock, factsMock):
        """Returns the country as text if a city is not available"""
        cacheGetMock.return_value = ({"foo": "bar"},)
        factsMock.return_value = {
            "geo": {
                "country_name": "test country"
            }
        }
        response = self.request("/", address="1.1.1.1", as_plain=True)
        self.assertEqual(response.body, "test country")

    @mock.patch("util.ip.facts")
    @mock.patch("util.cache.Cache.get")
    def test_textResponseUnknown(self, cacheGetMock, factsMock):
        """Returns the string Unknown if the geolocation cannot be determined"""
        cacheGetMock.return_value = ({"foo": "bar"},)
        factsMock.return_value = {
            "geo": {}
        }
        response = self.request("/", address="1.1.1.1", as_plain=True)
        self.assertTrue(response.code, 200)
        self.assertEqual(response.body, "Unknown")


    @mock.patch("util.ip.facts")
    @mock.patch("util.cache.Cache.get")
    def test_whoisPopulateNonUsMapParams(self, cacheGetMock, factsMock):
        """Defines the map region for a non-US IP as a 2-letter ISO code """
        cacheGetMock.return_value = ({"foo": "bar"},)
        factsMock.return_value = {
            "geo": {
                "country_code": "AU"
            }
        }
        response = self.request("/", address="1.1.1.1", as_json=True)
        self.assertEqual(response.body["map_region"], "AU")

    @mock.patch("socket.gethostbyaddr")
    @mock.patch("util.ip.facts")
    @mock.patch("util.cache.Cache.get")
    def test_reverseLookup(self, cacheGetMock, factsMock, getHostMock):
        """Performs a reverse IP lookup"""
        cacheGetMock.return_value = ({"foo": "bar"},)
        factsMock.return_value = {}
        getHostMock.return_value = ("example.com", [], [])
        response = self.request("/", address="1.1.1.1", as_json=True)

        self.assertEqual(response.body["reverse_host"], "example.com")
        self.assertTrue(getHostMock.called)

    @mock.patch("socket.gethostbyname_ex")
    @mock.patch("util.ip.facts")
    @mock.patch("util.cache.Cache.get")
    def test_hostToIp(self, cacheGetMock, factsMock, getHostMock):
        """Converts a hostname to an IP"""
        cacheGetMock.return_value = ({"foo": "bar"},)
        factsMock.return_value = {}
        getHostMock.return_value = ("example.com", [], ["1.1.1.1"])
        response = self.request("/", address="example.com", as_json=True)

        self.assertEqual(response.body["ip"], "1.1.1.1")
        self.assertTrue(getHostMock.called)

    @mock.patch("socket.gethostbyname_ex")
    @mock.patch("util.ip.facts")
    @mock.patch("util.cache.Cache.get")
    def test_hostToIpException(self, cacheGetMock, factsMock, getHostMock):
        """Handles exceptions from hostname to IP conversion"""
        cacheGetMock.return_value = ({"foo": "bar"},)
        factsMock.return_value = {}
        getHostMock.side_effect = Exception()
        response = self.request("/", address="example.com", as_json=True)

        self.assertEqual(response.code, 400)
        self.assertTrue(getHostMock.called)

if __name__ == "__main__":
    unittest.main()
