"""
Test suite for the alturl app
"""

import unittest
from testing.assertions import ResponseAssertions
from testing import helpers
from testing.cptestcase import BaseCherryPyTestCase
import apps.alturl.main


class TestAltUrl(BaseCherryPyTestCase, ResponseAssertions):
    """
    Tests for the application controller.
    """

    @classmethod
    def setUpClass(cls):
        """Start a faux cherrypy server"""
        helpers.start_server(apps.alturl.main.Controller)

    @classmethod
    def tearDownClass(cls):
        """Shut down the faux server"""
        helpers.stop_server()

    def test_allow(self):
        """Verify the controller's supported HTTP methods"""
        response = self.request("/", method="HEAD")
        self.assert_allowed(response, ("GET", "POST"))

    def test_exposed(self):
        """The application is publicly available."""
        self.assert_exposed(apps.alturl.main.Controller)

    def test_show_on_homepage(self):
        """The application is displayed in the homepage app."""
        self.assert_show_on_homepage(apps.alturl.main.Controller)


if __name__ == "__main__":
    unittest.main()
