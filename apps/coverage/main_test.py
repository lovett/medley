"""
Test suite for the coverage app
"""

import unittest
import mock
from testing.assertions import ResponseAssertions
from testing import helpers
from testing.cptestcase import BaseCherryPyTestCase
import apps.coverage.main


class TestCoverage(BaseCherryPyTestCase, ResponseAssertions):
    """
    Tests for the coverage application controller
    """

    @classmethod
    def setUpClass(cls):
        """Start a faux cherrypy server"""
        helpers.start_server(apps.coverage.main.Controller)

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
        self.assert_exposed(apps.coverage.main.Controller)

    def test_user_facing(self):
        """The application is displayed in the homepage app."""
        self.assert_user_facing(apps.coverage.main.Controller)

    @mock.patch("cherrypy.engine.publish")
    def test_redirect(self, publish_mock):
        """The controller's sole job is to redirect to the report."""

        def side_effect(*args, **_):
            """Side effects local function"""
            if args[0] == "url:internal":
                return ["/static/index.html"]

            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        response = self.request("/")
        self.assertEqual(response.code, 303)
        self.assertIn("/static/index.html", response.headers.get("Location"))


if __name__ == "__main__":
    unittest.main()
