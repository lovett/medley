"""
Test suite for the whois app
"""

import unittest
from testing.assertions import ResponseAssertions
from testing import helpers
from testing.cptestcase import BaseCherryPyTestCase
import apps.shared.main


class TestShared(BaseCherryPyTestCase, ResponseAssertions):
    """
    Tests for the application controller.
    """

    @classmethod
    def setUpClass(cls):
        helpers.start_server(apps.shared.main.Controller)

    @classmethod
    def tearDownClass(cls):
        helpers.stop_server()

    def test_allow(self):
        """Verify the controller's supported HTTP methods"""
        response = self.request("/", method="HEAD")
        self.assert_allowed(response, ("GET",))

    def test_exposed(self):
        """The application is publicly available."""
        self.assert_exposed(apps.shared.main.Controller)

    def test_not_user_facing(self):
        """The application is not displayed in the homepage app."""
        self.assert_not_user_facing(apps.shared.main.Controller)

    def test_redirect(self):
        """GET redirects to the homepage"""
        response = self.request("/")
        self.assertEqual(response.code, 303)


if __name__ == "__main__":
    unittest.main()
