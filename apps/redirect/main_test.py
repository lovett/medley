"""
Test suite for the redirect app
"""

import unittest
from testing.assertions import ResponseAssertions
from testing import helpers
from testing.cptestcase import BaseCherryPyTestCase
import apps.redirect.main


class TestRedirect(BaseCherryPyTestCase, ResponseAssertions):
    """
    Tests for the redirect application controller
    """

    @classmethod
    def setUpClass(cls):
        """Start a faux cherrypy server"""
        helpers.start_server(apps.redirect.main.Controller)

    @classmethod
    def tearDownClass(cls):
        """Shut down the faux server"""
        helpers.stop_server()

    def test_allow(self):
        """Verify the controller's supported HTTP methods"""
        response = self.request("/", method="HEAD")
        self.assert_allowed(response, ("GET",))

    def test_no_destination(self):
        """If no URL is provided, no redirect occurs."""
        response = self.request("/")

        self.assertEqual(response.code, 200)


if __name__ == "__main__":
    unittest.main()
