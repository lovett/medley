"""Test suite for the bucketpull app."""

import unittest
from testing.assertions import ResponseAssertions
from testing import helpers
from testing.cptestcase import BaseCherryPyTestCase
import apps.bucketpull.main


class TestBucketpull(BaseCherryPyTestCase, ResponseAssertions):
    """Tests for the application controller."""

    @classmethod
    def setUpClass(cls) -> None:
        """Start a faux cherrypy server"""
        helpers.start_server(apps.bucketpull.main.Controller)

    @classmethod
    def tearDownClass(cls) -> None:
        """Shut down the faux server"""
        helpers.stop_server()

    def test_allow(self) -> None:
        """Verify the controller's supported HTTP methods"""
        response = self.request("/", method="HEAD")
        self.assert_allowed(response, ("POST",))

    def test_exposed(self) -> None:
        """The application is publicly available."""
        self.assert_exposed(apps.bucketpull.main.Controller)

    def test_not_show_on_homepage(self) -> None:
        """The application is not displayed in the homepage app."""
        self.assert_not_show_on_homepage(apps.bucketpull.main.Controller)

    def test_service_missing(self) -> None:
        """The service to pull from is specified in the first URL segment."""

        response = self.request(
            "/",
            method="POST",
        )
        self.assert_404(response)

    def test_service_invalid(self) -> None:
        """A 404 is returned if the service specified in the URL is unknown."""

        response = self.request(
            "/whatever",
            method="POST",
        )

        self.assert_404(response)


if __name__ == "__main__":
    unittest.main()
