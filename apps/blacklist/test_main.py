"""Test suite for the blacklist app"""

import unittest
import mock
from testing.assertions import ResponseAssertions
from testing import helpers
from testing.cptestcase import BaseCherryPyTestCase
import apps.blacklist.main


class TestBlacklist(BaseCherryPyTestCase, ResponseAssertions):
    """Tests for the blacklist application controller."""

    @classmethod
    def setUpClass(cls):
        """Start a faux cherrypy server"""
        helpers.start_server(apps.blacklist.main.Controller)

    @classmethod
    def tearDownClass(cls):
        """Shut down the faux server"""
        helpers.stop_server()

    def test_allow(self):
        """Verify the controller's supported HTTP methods"""
        response = self.request("/", method="HEAD")
        self.assertAllowedMethods(response, ("PUT", "DELETE"))

    @mock.patch("cherrypy.engine.publish")
    def test_blacklist_sanitize(self, publish_mock):
        """Alphanumeric input is accepted."""

        def side_effect(*args, **_):
            """Side effects local function"""

            if args[0] == "formatting:phone_sanitize":
                return [123]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        response = self.request("/", method="PUT", number="x123")

        self.assertEqual(response.code, 204)

    @mock.patch("cherrypy.engine.publish")
    def test_unblacklist(self, publish_mock):
        """A previously blacklisted value can be removed."""

        def side_effect(*args, **_):
            """Side effects local function"""

            if args[0] == "formatting:phone_sanitize":
                return [9998887777]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        response = self.request("/", method="DELETE", number="9998887777")

        self.assertEqual(response.code, 204)


if __name__ == "__main__":
    unittest.main()
