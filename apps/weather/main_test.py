"""
Test suite for the weather app
"""

import unittest
import mock
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

    @mock.patch("cherrypy.engine.publish")
    def test_returns_html(self, publish_mock):
        """Request should return HTML"""
        pass


if __name__ == "__main__":
    unittest.main()
