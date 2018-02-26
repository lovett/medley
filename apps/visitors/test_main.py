"""
Test suite for the visitors app
"""

import unittest
from testing.assertions import ResponseAssertions
from testing import helpers
from testing.cptestcase import BaseCherryPyTestCase
import apps.visitors.main


class TestVisitors(BaseCherryPyTestCase, ResponseAssertions):
    """
    Tests for the visitors application controller
    """

    @classmethod
    def setUpClass(cls):
        helpers.start_server(apps.visitors.main.Controller)

    @classmethod
    def tearDownClass(cls):
        helpers.stop_server()

    def test_allow(self):
        """Verify the controller's supported HTTP methods"""
        response = self.request("/", method="HEAD")
        self.assertAllowedMethods(response, ("GET",))


if __name__ == "__main__":
    unittest.main()
