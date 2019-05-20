"""
Test suite for the wakeup app
"""

import unittest
from testing.assertions import ResponseAssertions
from testing import helpers
from testing.cptestcase import BaseCherryPyTestCase
import apps.wakeup.main


class TestWakeup(BaseCherryPyTestCase, ResponseAssertions):
    """
    Tests for the wakeup application controller
    """

    @classmethod
    def setUpClass(cls):
        helpers.start_server(apps.wakeup.main.Controller)

    @classmethod
    def tearDownClass(cls):
        helpers.stop_server()

    def test_allow(self):
        """Verify the controller's supported HTTP methods"""
        response = self.request("/", method="HEAD")
        self.assertAllowedMethods(response, ("GET", "POST"))


if __name__ == "__main__":
    unittest.main()
