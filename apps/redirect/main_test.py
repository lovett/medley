"""Test suite for the redirect app."""

import typing
import unittest
import mock
from testing.assertions import ResponseAssertions
from testing import helpers
from testing.cptestcase import BaseCherryPyTestCase
import apps.redirect.main


class TestRedirect(BaseCherryPyTestCase, ResponseAssertions):
    """Tests for the application controller."""

    @classmethod
    def setUpClass(cls) -> None:
        """Start a faux cherrypy server"""
        helpers.start_server(apps.redirect.main.Controller)

    @classmethod
    def tearDownClass(cls) -> None:
        """Shut down the faux server"""
        helpers.stop_server()

    def test_allow(self) -> None:
        """Verify the controller's supported HTTP methods"""
        response = self.request("/", method="HEAD")
        self.assert_allowed(response, ("GET",))

    def test_exposed(self) -> None:
        """The application is publicly available."""
        self.assert_exposed(apps.redirect.main.Controller)

    def test_not_show_on_homepage(self) -> None:
        """The application is not displayed in the homepage app."""
        self.assert_not_show_on_homepage(apps.redirect.main.Controller)

    @mock.patch("cherrypy.engine.publish")
    def test_no_destination(self, publish_mock: mock.Mock) -> None:
        """If no URL is provided, no redirect occurs."""

        def side_effect(*args: str, **_kwargs: str) -> typing.Any:
            """Side effects local function"""
            if args[0] == "jinja:render":
                return [""]

            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        response = self.request("/")

        self.assertEqual(response.code, 200)


if __name__ == "__main__":
    unittest.main()
