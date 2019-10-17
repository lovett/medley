"""
Test suite for the maintenance app
"""

import unittest
import mock
from testing.assertions import ResponseAssertions
from testing import helpers
from testing.cptestcase import BaseCherryPyTestCase
import apps.maintenance.main


class TestLater(BaseCherryPyTestCase, ResponseAssertions):
    """
    Tests for the maintenance application controller
    """

    @classmethod
    def setUpClass(cls):
        """Start a faux cherrypy server"""
        helpers.start_server(apps.maintenance.main.Controller)

    @classmethod
    def tearDownClass(cls):
        """Shut down the faux server"""
        helpers.stop_server()

    def test_allow(self):
        """Verify the controller's supported HTTP methods"""
        response = self.request("/", method="HEAD")
        self.assert_allowed(response, ("POST",))

    def test_group_required(self):
        """The group parameter must be specified."""
        response = self.request(
            "/",
            method="POST"
        )
        self.assertEqual(response.code, 400)

    def test_group_valid(self):
        """The group parameter must be valid."""
        response = self.request(
            "/",
            method="POST",
            group="test"
        )
        self.assertEqual(response.code, 400)

    @mock.patch("cherrypy.engine.publish")
    def test_invokes_scheduler(self, publish_mock):
        """The maintenance plug is invoked via the scheduler."""
        response = self.request(
            "/",
            method="POST",
            group="db"
        )

        def side_effect(*args, **_):
            """Side effects local function"""
            if args[0] == "scheduler:add":
                self.assertEqual(args[2], "maintenance:db")
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        self.assertEqual(response.code, 204)


if __name__ == "__main__":
    unittest.main()
