from testing import cptestcase
from testing import helpers
from testing import assertions
import unittest
import mock
import apps.countries.main


class TestCountries(cptestcase.BaseCherryPyTestCase, assertions.ResponseAssertions):
    @classmethod
    def setUpClass(cls):
        helpers.start_server(apps.countries.main.Controller)

    @classmethod
    def tearDownClass(cls):
        helpers.stop_server()

    def setUp(self):
        self.fixture = [{
	    "Capital": "Washington",
	    "Continent": "NA",
	    "DS": "USA",
	    "Dial": "1",
	    "EDGAR": "",
	    "FIFA": "USA",
	    "FIPS": "US",
	    "GAUL": "259",
	    "Geoname ID": 6252001.0,
	    "IOC": "USA",
	    "ISO3166-1-Alpha-2": "US",
	    "ISO3166-1-Alpha-3": "USA",
	    "ISO4217-currency_alphabetic_code": "USD",
	    "ISO4217-currency_country_name": "UNITED STATES",
	    "ISO4217-currency_minor_unit": 2.0,
	    "ISO4217-currency_name": "US Dollar",
	    "ISO4217-currency_numeric_code": 840.0,
	    "ITU": "USA",
	    "Languages": "en-US,es-US,haw,fr",
	    "M49": 840.0,
	    "MARC": "xxu",
	    "TLD": ".us",
	    "WMO": "US",
	    "is_independent": "Yes",
	    "name": "US",
	    "official_name_en": "United States of America",
	    "official_name_fr": "États-Unis d'Amérique"
	}]

    def default_side_effect_callback(self, *args, **kwargs):
        if args[0] == "cache:get":
            return [self.fixture]

    def uncached_side_effect_callback(self, *args, **kwargs):
        if args[0] == "cache:get":
            return [None]
        if args[0] == "urlfetch:get":
            return [self.fixture]

    def failure_side_effect_callback(self, *args, **kwargs):
        if args[0] == "cache:get":
            return [None]
        if args[0] == "urlfetch:get":
            return [None]

    def test_allow(self):
        response = self.request("/", method="HEAD")
        self.assertAllowedMethods(response, ("GET",))

    @mock.patch("cherrypy.engine.publish")
    def testRegistrySave(self, publishMock):
        """Country codes are saved to the registry"""

        publishMock.side_effect = self.default_side_effect_callback

        response = self.request("/")

        self.assertEqual(response.code, 204)

        publishMock.assert_called_with("registry:add", "country_code:alpha2:US", "US", True)


    @mock.patch("cherrypy.engine.publish")
    def testUrlFetchedIfNotCached(self, publishMock):
        """The JSON file is fetched if it is not already in the cache"""

        publishMock.side_effect = self.uncached_side_effect_callback

        response = self.request("/")

        self.assertEqual(response.code, 204)

        publishMock.assert_any_call("cache:set", "countries", self.fixture)
        publishMock.assert_any_call("registry:add", "country_code:alpha2:US", "US", True)

    @mock.patch("cherrypy.engine.publish")
    def testUrlFetchFailure(self, publishMock):
        """An error is returned if the list of country codes cannot be fetched"""

        publishMock.side_effect = self.failure_side_effect_callback

        response = self.request("/")

        self.assertEqual(response.code, 501)




if __name__ == "__main__":
    unittest.main()
