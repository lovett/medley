"""
Test suite for the logindex app
"""

import unittest
import pendulum
import mock
from testing.assertions import ResponseAssertions
from testing import helpers
from testing.cptestcase import BaseCherryPyTestCase
import apps.logindex.main


class TestLater(BaseCherryPyTestCase, ResponseAssertions):
    """
    Tests for the whois application controller
    """

    @classmethod
    def setUpClass(cls):
        """Start a faux cherrypy server"""
        helpers.start_server(apps.logindex.main.Controller)

    @classmethod
    def tearDownClass(cls):
        """Shut down the faux server"""
        helpers.stop_server()

    def test_allow(self):
        """Verify the controller's supported HTTP methods"""
        response = self.request("/", method="HEAD")
        self.assertAllowedMethods(response, ("POST",))

    def test_invalid_start(self):
        """An error should be thrown if the start date cannot be parsed"""
        response = self.request(
            "/",
            method="POST",
            start="invalid"
        )
        self.assertEqual(response.code, 400)

    def test_invalid_end(self):
        """An error should be thrown if the end date cannot be parsed"""
        response = self.request(
            "/",
            method="POST",
            start="2000-01-01.log",
            end="1999-12-31.log"
        )
        self.assertEqual(response.code, 400)

    @mock.patch("cherrypy.engine.publish")
    def test_valid_range(self, publish_mock):
        """
        The logindex plugin is called when a valid time range is given.
        """

        self.request(
            "/",
            method="POST",
            start="2017-01-01.log",
            end="2017-01-03.log"
        )

        calls = publish_mock.call_args_list

        self.assertEqual(
            calls[-4],
            mock.call('logindex:enqueue', pendulum.create(2017, 1, 1, 0, 0))
        )

        self.assertEqual(
            calls[-3],
            mock.call('logindex:enqueue', pendulum.create(2017, 1, 2, 0, 0))
        )

        self.assertEqual(
            calls[-2],
            mock.call('logindex:enqueue', pendulum.create(2017, 1, 3, 0, 0))
        )

        self.assertEqual(
            calls[-1],
            mock.call('logindex:parse')
        )

    @mock.patch("cherrypy.engine.publish")
    def test_only_start(self, publish_mock):
        """
        A single-day time range can be specified by only specifying the
        start date.
        """
        self.request(
            "/",
            method="POST",
            start="2017-01-01.log"
        )

        calls = publish_mock.call_args_list

        self.assertEqual(
            calls[-2],
            mock.call('logindex:enqueue', pendulum.create(2017, 1, 1, 0, 0))
        )

        self.assertEqual(
            calls[-1], mock.call('logindex:parse')
        )


if __name__ == "__main__":
    unittest.main()
