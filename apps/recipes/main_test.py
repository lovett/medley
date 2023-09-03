"""Test suite for the recipes app."""

import unittest
from testing.assertions import ResponseAssertions
from testing import helpers
from testing.cptestcase import BaseCherryPyTestCase
import apps.recipes.main  # type: ignore


class TestRecipes(BaseCherryPyTestCase, ResponseAssertions):

    @classmethod
    def setUpClass(cls) -> None:
        helpers.start_server(apps.recipes.main.Controller)

    @classmethod
    def tearDownClass(cls) -> None:
        helpers.stop_server()

    def test_allow(self) -> None:
        """Verify the controller's supported HTTP methods"""
        response = self.request("/", method="HEAD")
        self.assert_allowed(response, ("GET", "POST", "PATCH", "DELETE"))

    def test_exposed(self) -> None:
        """The application is publicly available."""
        self.assert_exposed(apps.recipes.main.Controller)

    def test_show_on_homepage(self) -> None:
        """The application is displayed in the homepage app."""
        self.assert_show_on_homepage(apps.recipes.main.Controller)


if __name__ == "__main__":
    unittest.main()
