"""Test suite for the sleeplog app."""

import unittest
from testing.assertions import ResponseAssertions
from testing import helpers
from testing.cptestcase import BaseCherryPyTestCase
import apps.sleeplog.main  # type: ignore


class TestSleeplog(BaseCherryPyTestCase, ResponseAssertions):

    @classmethod
    def setUpClass(cls) -> None:
        helpers.start_server(apps.sleeplog.main.Controller)

    @classmethod
    def tearDownClass(cls) -> None:
        helpers.stop_server()

    def test_allow(self) -> None:
        """Verify the controller's supported HTTP methods"""
        response = self.request("/", method="HEAD")
        self.assert_allowed(response, ("GET", "POST", "DELETE"))

    def test_exposed(self) -> None:
        """The application is publicly available."""
        self.assert_exposed(apps.sleeplog.main.Controller)

    def test_show_on_homepage(self) -> None:
        """The application is displayed in the homepage app."""
        self.assert_show_on_homepage(apps.sleeplog.main.Controller)


if __name__ == "__main__":
    unittest.main()
