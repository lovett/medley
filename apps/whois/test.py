import cptestcase
import helpers
import unittest
import responses
import apps.whois.main
import mock
import util.db
import time

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
        self.assertTrue(cacheGetMock.called)
        self.assertFalse(cacheSetMock.called)
        self.assertTrue(ipFactsMock.called)

    @mock.patch("apps.whois.main.Controller.resolveHost")
    @mock.patch("util.db.ipFacts")
    @mock.patch("util.db.cacheSet")
    @mock.patch("util.db.cacheGet")
    def xtest_addressAsInvalidHostname(self, cacheGetMock, cacheSetMock, ipFactsMock, resolveHostMock):
        """Queries the geoip database"""
        cacheGetMock.return_value = ({},)
        ipFactsMock.return_value = {}
        resolveHostMock.return_value = "1.1.1.1"
        response = self.request("/", address="invalid", as_json=True)
        self.assertTrue(cacheGetMock.called)
        self.assertFalse(cacheSetMock.called)
        self.assertTrue(ipFactsMock.called)


    @mock.patch("util.db.geoip")
    @mock.patch("util.net.resolveHost")
    @mock.patch("util.net.whois")
    def xtest_whoisInputHostname(self, whoisMock, resolveHostMock, geoipMock):
        """ /whois accepts a hostname as input """
        whoisMock.return_value = {}
        resolveHostMock.return_value = "1.1.1.1"
        geoipMock.side_effect = Exception('Force fail')
        response = self.request("/whois/example.com", as_json=True)
        self.assertEqual(response.body["ip"], "1.1.1.1")

    @mock.patch("util.db.geoip")
    @mock.patch("util.net.resolveHost")
    @mock.patch("util.net.whois")
    def xtest_whoisInputUrl(self, whoisMock, resolveHostMock, geoipMock):
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
    def xtest_whoisInputHostAlias(self, whoisMock, resolveHostMock, geoipMock):
        """ /whois accepts a host alias as input """
        whoisMock.return_value = {}
        resolveHostMock.return_value = "1.1.1.1"
        geoipMock.side_effect = Exception('Force fail')
        response = self.request("/whois/foo", as_json=True)
        self.assertEqual(response.body["ip"], "1.1.1.1")



    @mock.patch("util.db.geoip")
    @mock.patch("util.net.whois")
    def xtest_whoisPopulateUsMapParams(self, queryWhoisMock, geoipMock):
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
    def xtest_whoisPopulateNonUsMapParams(self, queryWhoisMock, geoipMock):
        """ /whois defines the map region for a non-US IP as a 2-letter ISO code """
        queryWhoisMock.return_value = {}
        geoipMock.return_value = {
            "country_code": "AU"
        }
        response = self.request("/whois/1.1.1.1", as_json=True)
        self.assertEqual(response.body["map_region"], "AU")

    @mock.patch("util.db.geoip")
    @mock.patch("util.net.whois")
    def xtest_whoisSkipsGeoipQuery(self, queryWhoisMock, geoipMock):
        """ /whois returns success if the geoip query fails """
        queryWhoisMock.return_value = {}
        geoipMock.side_effect = Exception('Force fail')
        response = self.request("/whois/1.1.1.1", as_json=True)
        self.assertTrue(response.code, 200)


    @mock.patch("util.db.geoip")
    @mock.patch("util.net.whois")
    def xtest_whoisPlainReturnsCityAndCountry(self, queryWhoisMock, geoipMock):
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
    def xtest_whoisPlainReturnsCountry(self, queryWhoisMock, geoipMock):
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
    def xtest_whoisPlainReturnsUnknown(self, queryWhoisMock, geoipMock):
        """ /whois returns "Unknown" if city and country name are not available"""
        geoipMock.return_value = {}
        queryWhoisMock.return_value = {}
        response = self.request("/whois/1.1.1.1", as_plain=True)
        self.assertEqual(response.body, "Unknown")



if __name__ == "__main__":
    unittest.main()
