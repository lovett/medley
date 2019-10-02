"""
Test suite for the geography plugin
"""

import json
import unittest
import mock
import cherrypy
from testing import helpers
import plugins.geography


class TestGeography(unittest.TestCase):
    """
    Tests for the geography plugin
    """

    def setUp(self):
        self.plugin = plugins.geography.Plugin(cherrypy.engine)

    @mock.patch("cherrypy.engine.publish")
    def test_state_name_invalid(self, publish_mock):
        """An invalid state abbreviation returns Unknown for the state name"""

        def side_effect(*args, **_):
            """Side effects local function"""

            if args[0] == "urlfetch:get":
                fixture = json.loads(
                    helpers.getFixture("dbpedia-state-fail.json")
                )
                return [fixture]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        query, result = self.plugin.unabbreviate_us_state("x")
        self.assertTrue("US-x" in query)
        self.assertIsNone(result)

    @mock.patch("cherrypy.engine.publish")
    def test_state_name_valid(self, publish_mock):
        """A valid state abbreviation returns the correct state name"""

        def side_effect(*args, **_):
            """Side effects local function"""

            if args[0] == "urlfetch:get":
                fixture = json.loads(
                    helpers.getFixture("dbpedia-state-success.json")
                )
                return [fixture]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        query, result = self.plugin.unabbreviate_us_state("NY")

        self.assertTrue("US-NY" in query)
        self.assertEqual(result, "New York")


if __name__ == "__main__":
    unittest.main()
