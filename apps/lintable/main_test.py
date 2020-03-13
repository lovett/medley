"""Test suite for the lintable app."""

import unittest
from testing.assertions import ResponseAssertions
from testing import helpers
from testing.cptestcase import BaseCherryPyTestCase
import apps.lintable.main


class TestLintable(BaseCherryPyTestCase, ResponseAssertions):
    """
    Tests for the application controller.
    """

    @classmethod
    def setUpClass(cls) -> None:
        helpers.start_server(apps.lintable.main.Controller)

    @classmethod
    def tearDownClass(cls) -> None:
        helpers.stop_server()

    def test_allow(self) -> None:
        """Verify the controller's supported HTTP methods"""
        response = self.request("/", method="HEAD")
        self.assert_allowed(response, ("GET", "PUT"))

    def test_exposed(self) -> None:
        """The application is publicly available."""
        self.assert_exposed(apps.lintable.main.Controller)

    def test_not_shown_on_homepage(self) -> None:
        """The application is not displayed in the homepage app."""
        self.assert_not_show_on_homepage(apps.lintable.main.Controller)


if __name__ == "__main__":
    unittest.main()
