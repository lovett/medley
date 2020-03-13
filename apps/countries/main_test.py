"""Test suite for the countries app."""

import typing
import unittest
import mock
from testing.assertions import ResponseAssertions
from testing import helpers
from testing.cptestcase import BaseCherryPyTestCase
import apps.countries.main


class TestCountries(BaseCherryPyTestCase, ResponseAssertions):
    """
    Tests for the application controller.
    """

    @classmethod
    def setUpClass(cls) -> None:
        helpers.start_server(apps.countries.main.Controller)

    @classmethod
    def tearDownClass(cls) -> None:
        helpers.stop_server()

    def setUp(self) -> None:
        self.fixture = [{
            "CLDR display name": "US",
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
            "official_name_en": "USA",
            "official_name_fr": "États-Unis d'Amérique"
        }]

    def test_allow(self) -> None:
        """Verify the controller's supported HTTP methods"""
        response = self.request("/", method="HEAD")
        self.assert_allowed(response, ("GET",))

    def test_exposed(self) -> None:
        """The application is publicly available."""
        self.assert_exposed(apps.countries.main.Controller)

    def test_not_show_on_homepage(self) -> None:
        """The application is not displayed in the homepage app."""
        self.assert_not_show_on_homepage(apps.countries.main.Controller)

    @mock.patch("cherrypy.engine.publish")
    def test_registry_save(self, publish_mock: mock.Mock) -> None:
        """Country codes are saved to the registry"""

        def side_effect(*args: str, **_: str) -> typing.Any:
            """Side effects local function"""
            if args[0] == "cache:get":
                return [self.fixture]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        response = self.request("/")

        self.assertEqual(response.code, 204)

        publish_mock.assert_called_with(
            "registry:replace",
            "country_code:alpha2:US",
            "US"
        )

    @mock.patch("cherrypy.engine.publish")
    def test_skip_record_without_name(self, publish_mock: mock.Mock) -> None:
        """A record without a name field is skipped."""

        def side_effect(*args: str, **_: str) -> typing.Any:
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
        # so make sure the last one wasn't registry:replace
        last_call = publish_mock.call_args[0][0]

        self.assertEqual(last_call, "cache:get")

    @mock.patch("cherrypy.engine.publish")
    def test_url_fetched_if_not_cached(self, publish_mock: mock.Mock) -> None:
        """The JSON file is fetched if it is not already in the cache"""

        def side_effect(*args: str, **_: str) -> typing.Any:
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
            "registry:replace",
            "country_code:alpha2:US",
            "US"
        )

    @mock.patch("cherrypy.engine.publish")
    def test_url_fetch_failure(self, publish_mock: mock.Mock) -> None:
        """
        An error is returned if the list of country codes cannot be
        fetched
        """

        def side_effect(*args: str, **_: str) -> typing.Any:
            """Side effects local function"""
            if args[0] in ("cache:get", "urlfetch:get"):
                return [None]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        response = self.request("/")

        self.assertEqual(response.code, 501)


if __name__ == "__main__":
    unittest.main()
