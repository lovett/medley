"""
Test suite for the weather app
"""

import unittest
from testing.assertions import ResponseAssertions
from testing import helpers
from testing.cptestcase import BaseCherryPyTestCase
import apps.weather.main


class TestWeather(BaseCherryPyTestCase, ResponseAssertions):
    """
    Tests for the weather application controller
    """

    @classmethod
    def setUpClass(cls):
        """Start a faux cherrypy server"""
        helpers.start_server(apps.weather.main.Controller)

    @classmethod
    def tearDownClass(cls):
        """Shut down the faux server"""
        helpers.stop_server()

    def test_exposed(self):
        """The application is publicly available."""
        self.assert_exposed(apps.weather.main.Controller)

    def test_user_facing(self):
        """The application is displayed in the homepage app."""
        self.assert_user_facing(apps.weather.main.Controller)


if __name__ == "__main__":
    unittest.main()
