"""Test suite for the headlines app."""

from typing import Any
import unittest
from unittest import mock
from testing.assertions import ResponseAssertions
from testing import helpers
from testing.cptestcase import BaseCherryPyTestCase
import apps.headlines.main  # type: ignore


class TestHeadlines(BaseCherryPyTestCase, ResponseAssertions):

    @classmethod
    def setUpClass(cls) -> None:
        """Start a faux cherrypy server."""
        helpers.start_server(apps.headlines.main.Controller)

    @classmethod
    def tearDownClass(cls) -> None:
        """Shut down the faux server."""
        helpers.stop_server()

    def test_allow(self) -> None:
        """Verify the controller's supported HTTP methods"""

    def test_exposed(self) -> None:
        """The application is publicly available."""
        self.assert_exposed(apps.headlines.main.Controller)

    def test_show_on_homepage(self) -> None:
        """The application is displayed in the homepage app."""
        self.assert_show_on_homepage(apps.headlines.main.Controller)

        response = self.request("/", method="HEAD")
        self.assert_allowed(response, ("GET",))


if __name__ == "__main__":
    unittest.main()
