"""Test suite for the geography plugin."""

import json
import typing
import unittest
from unittest.mock import Mock, patch, DEFAULT
import cherrypy
import plugins.geography
from testing import helpers
from testing.assertions import Subscriber


class TestGeography(Subscriber):
    """
    Tests for the geography plugin.
    """

    def setUp(self) -> None:
        self.plugin = plugins.geography.Plugin(cherrypy.engine)

    @patch("cherrypy.engine.subscribe")
    def test_subscribe(self, subscribe_mock: Mock) -> None:
        """Subscriptions are prefixed consistently."""

        self.plugin.start()
        self.assert_prefix(subscribe_mock, "geography")

    @patch("cherrypy.engine.publish")
    def test_area_code_valid(self, publish_mock: Mock) -> None:
        """A triple is returned if the area code is valid"""

        def side_effect(*args: str, **_: str) -> typing.Any:
            """Side effects local function"""

            if args[0] == "urlfetch:get":
                fixture = json.loads(
                    helpers.get_fixture("dbpedia-area-success.json")
                )
                return [fixture]
            return DEFAULT

        publish_mock.side_effect = side_effect

        result = self.plugin.state_by_area_code("212")

        self.assertTrue("dbpedia" in result[0])
        self.assertEqual(result[1], "NY")

    @patch("cherrypy.engine.publish")
    def test_area_code_invalid(self, publish_mock: Mock) -> None:
        """A triple is returned if the area code is valid"""

        def side_effect(*args: str, **_: str) -> typing.Any:
            """Side effects local function"""

            if args[0] == "urlfetch:get":
                fixture = json.loads(
                    helpers.get_fixture("dbpedia-area-fail.json")
                )
                return [fixture]
            return DEFAULT

        publish_mock.side_effect = side_effect

        result = self.plugin.state_by_area_code("000")

        self.assertTrue("dbpedia" in result[0])
        self.assertIsNone(result[1])
        self.assertIsNone(result[2])

    @patch("cherrypy.engine.publish")
    def test_state_name_invalid(self, publish_mock: Mock) -> None:
        """An invalid state abbreviation returns Unknown for the state name"""

        def side_effect(*args: str, **_: str) -> typing.Any:
            """Side effects local function"""

            if args[0] == "urlfetch:get":
                fixture = json.loads(
                    helpers.get_fixture("dbpedia-state-fail.json")
                )
                return [fixture]
            return DEFAULT

        publish_mock.side_effect = side_effect

        query, result = self.plugin.unabbreviate_us_state("x")
        self.assertTrue("US-x" in query)
        self.assertIsNone(result)

    @patch("cherrypy.engine.publish")
    def test_state_name_valid(self, publish_mock: Mock) -> None:
        """A valid state abbreviation returns the correct state name"""

        def side_effect(*args: str, **_kwargs: str) -> typing.Any:
            """Side effects local function"""

            if args[0] == "urlfetch:get":
                fixture = json.loads(
                    helpers.get_fixture("dbpedia-state-success.json")
                )
                return [fixture]
            return DEFAULT

        publish_mock.side_effect = side_effect

        query, result = self.plugin.unabbreviate_us_state("NY")

        self.assertTrue("US-NY" in query)
        self.assertEqual(result, "New York")


if __name__ == "__main__":
    unittest.main()
