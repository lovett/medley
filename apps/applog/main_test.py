"""
Test suite for the applog app
"""

import unittest
from testing.assertions import ResponseAssertions
from testing import helpers
from testing.cptestcase import BaseCherryPyTestCase
import apps.applog.main


class TestApplog(BaseCherryPyTestCase, ResponseAssertions):
    """
    Tests for the applog application controller
    """

    @classmethod
    def setUpClass(cls):
        """Start a faux cherrypy server"""
        helpers.start_server(apps.applog.main.Controller)

    @classmethod
    def tearDownClass(cls):
        """Shut down the faux server"""
        helpers.stop_server()

    def test_allow(self):
        """Verify the controller's supported HTTP methods"""
        response = self.request("/", method="HEAD")
        self.assert_allowed(response, ("GET",))

    def test_exposed(self):
        """The application is publicly available."""
        self.assert_exposed(apps.applog.main.Controller)

    def test_user_facing(self):
        """The application is displayed in the homepage app."""
        self.assert_user_facing(apps.applog.main.Controller)


if __name__ == "__main__":
    unittest.main()