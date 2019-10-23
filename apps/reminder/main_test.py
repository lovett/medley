"""
Test suite for the reminder app.
"""

import unittest
from testing.assertions import ResponseAssertions
from testing import helpers
from testing.cptestcase import BaseCherryPyTestCase
import apps.reminder.main


class TestReminder(BaseCherryPyTestCase, ResponseAssertions):
    """
    Tests for the reminder application controller.
    """

    @classmethod
    def setUpClass(cls):
        helpers.start_server(apps.reminder.main.Controller)

    @classmethod
    def tearDownClass(cls):
        helpers.stop_server()

    def test_allow(self):
        """Verify the controller's supported HTTP methods."""
        response = self.request("/", method="HEAD")
        self.assert_allowed(response, ("GET", "POST", "DELETE"))

    def test_exposed(self):
        """The application is publicly available."""
        self.assert_exposed(apps.reminder.main.Controller)

    def test_user_facing(self):
        """The application is displayed in the homepage app."""
        self.assert_user_facing(apps.reminder.main.Controller)


if __name__ == "__main__":
    unittest.main()
