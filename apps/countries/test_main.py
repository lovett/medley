"""
Test suite for the countries app
"""

import unittest
import mock
from testing.assertions import ResponseAssertions
from testing import helpers
from testing.cptestcase import BaseCherryPyTestCase
import apps.countries.main


class TestCountries(BaseCherryPyTestCase, ResponseAssertions):
    """
    Tests for the jenkins application controller
    """

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

    def test_allow(self):
        """Verify the controller's supported HTTP methods"""
        response = self.request("/", method="HEAD")
        self.assertAllowedMethods(response, ("GET",))

    @mock.patch("cherrypy.engine.publish")
    def test_registry_save(self, publish_mock):
        """Country codes are saved to the registry"""

        def side_effect(*args, **_):
            """Side effects local function"""
            if args[0] == "cache:get":
                return [self.fixture]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        response = self.request("/")

        self.assertEqual(response.code, 204)

        publish_mock.assert_called_with(
            "registry:add",
            "country_code:alpha2:US",
            ("United States of America",),
            True
        )

    @mock.patch("cherrypy.engine.publish")
    def test_skip_record_without_name(self, publish_mock):
        """A record without a name field is skipped."""

        def side_effect(*args, **_):
            """Side effects local function."""

            if args[0] == "cache:get":
                return [[{
                    "Capital": "Fake",
                    "Continent": "X",
                }]]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        response = self.request("/")

        self.assertEqual(response.code, 204)

        # There is no assert_not_called_with() method,
        # so make sure the last one wasn't registry:add
        last_call = publish_mock.call_args[0][0]

        self.assertEqual(last_call, "cache:get")

    @mock.patch("cherrypy.engine.publish")
    def test_url_fetched_if_not_cached(self, publish_mock):
        """The JSON file is fetched if it is not already in the cache"""

        def side_effect(*args, **_):
            """Side effects local function"""
            if args[0] == "cache:get":
                return [None]
            if args[0] == "urlfetch:get":
                return [self.fixture]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        response = self.request("/")

        self.assertEqual(response.code, 204)

        publish_mock.assert_any_call(
            "cache:set",
            "countries",
            self.fixture
        )

        publish_mock.assert_any_call(
            "registry:add",
            "country_code:alpha2:US",
            ("United States of America",),
            True
        )

    @mock.patch("cherrypy.engine.publish")
    def test_url_fetch_failure(self, publish_mock):
        """
        An error is returned if the list of country codes cannot be
        fetched
        """

        def side_effect(*args, **_):
            """Side effects local function"""
            if args[0] in ("cache:get", "urlfetch:get"):
                return [None]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        response = self.request("/")

        self.assertEqual(response.code, 501)


if __name__ == "__main__":
    unittest.main()
