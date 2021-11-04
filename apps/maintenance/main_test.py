"""Test suite for the maintenance app."""

import unittest
from unittest import mock
from testing.assertions import ResponseAssertions
from testing import helpers
from testing.cptestcase import BaseCherryPyTestCase
import apps.maintenance.main  # type: ignore


class TestLater(BaseCherryPyTestCase, ResponseAssertions):
    """
    Tests for the application controller.
    """

    @classmethod
    def setUpClass(cls) -> None:
        """Start a faux cherrypy server"""
        helpers.start_server(apps.maintenance.main.Controller)

    @classmethod
    def tearDownClass(cls) -> None:
        """Shut down the faux server"""
        helpers.stop_server()

    def test_allow(self) -> None:
        """Verify the controller's supported HTTP methods"""
        response = self.request("/", method="HEAD")
        self.assert_allowed(response, ("POST", "DELETE"))

    def test_exposed(self) -> None:
        """The application is publicly available."""
        self.assert_exposed(apps.maintenance.main.Controller)

    def test_not_show_on_homepage(self) -> None:
        """The application is not_displayed in the homepage app."""
        self.assert_not_show_on_homepage(apps.maintenance.main.Controller)

    @mock.patch("cherrypy.engine.publish")
    def test_invokes_scheduler(self, publish_mock: mock.Mock) -> None:
        """The maintenance plugin is invoked via the scheduler."""

        response = self.request(
            "/",
            method="POST"
        )

        self.assertEqual(response.code, 204)
        publish_mock.assert_called_with(
            "scheduler:add", 2, "maintenance"
        )

    @mock.patch("cherrypy.engine.publish")
    def test_delete_memorize(self, publish_mock: mock.Mock) -> None:
        """The memorize cache can be deleted with a DELETE request."""

        db_response = self.request(
            "/memorize",
            method="DELETE",
        )

        self.assertEqual(db_response.code, 204)
        publish_mock.assert_called_with(
            "memorize:clear"
        )

    def test_delete(self) -> None:
        """DELETE requests only recognize url paths."""

        response = self.request(
            "/",
            method="DELETE",
        )

        self.assertEqual(response.code, 404)

        response = self.request(
            "/whatever",
            method="DELETE",
        )

        self.assertEqual(response.code, 404)


if __name__ == "__main__":
    unittest.main()
