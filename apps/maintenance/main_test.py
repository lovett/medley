"""Test suite for the maintenance app."""

import unittest
from unittest import mock
from testing.assertions import ResponseAssertions
from testing import helpers
from testing.cptestcase import BaseCherryPyTestCase
import apps.maintenance.main


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
        self.assert_allowed(response, ("POST",))

    def test_exposed(self) -> None:
        """The application is publicly available."""
        self.assert_exposed(apps.maintenance.main.Controller)

    def test_not_show_on_homepage(self) -> None:
        """The application is not_displayed in the homepage app."""
        self.assert_not_show_on_homepage(apps.maintenance.main.Controller)

    def test_group_required(self) -> None:
        """The group parameter must be specified."""
        response = self.request(
            "/",
            method="POST"
        )
        self.assertEqual(response.code, 400)

    def test_group_valid(self) -> None:
        """The group parameter must be valid."""
        response = self.request(
            "/",
            method="POST",
            group="test"
        )
        self.assertEqual(response.code, 400)

    @mock.patch("cherrypy.engine.publish")
    def test_invokes_scheduler(self, publish_mock: mock.Mock) -> None:
        """The maintenance plug is invoked via the scheduler."""

        db_response = self.request(
            "/",
            method="POST",
            group="db"
        )

        self.assertEqual(db_response.code, 204)
        publish_mock.assert_called_with(
            "scheduler:add", 2, "maintenance:db"
        )

        fs_response = self.request(
            "/",
            method="POST",
            group="db"
        )

        self.assertEqual(fs_response.code, 204)
        publish_mock.assert_called_with(
            "scheduler:add", 2, "maintenance:db"
        )


if __name__ == "__main__":
    unittest.main()
