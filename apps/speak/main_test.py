"""
Test suite for the speak app
"""

import unittest
import mock
from testing.assertions import ResponseAssertions
from testing import helpers
from testing.cptestcase import BaseCherryPyTestCase
import apps.speak.main


class TestSpeak(BaseCherryPyTestCase, ResponseAssertions):
    """
    Tests for the speak application controller
    """

    @classmethod
    def setUpClass(cls):
        """Start a faux cherrypy server"""
        helpers.start_server(apps.speak.main.Controller)

    @classmethod
    def tearDownClass(cls):
        """Shut down the faux server"""
        helpers.stop_server()

    def test_allow(self):
        """Verify the controller's supported HTTP methods"""
        response = self.request("/", method="HEAD")
        self.assertAllowedMethods(response, ("GET", "HEAD", "POST"))

    @mock.patch("cherrypy.engine.publish")
    def test_muted(self, publish_mock):
        """If the application is muted, responses are returned with 202"""

        def side_effect(*args, **_):
            """Side effects local function"""

            if args[0] == "speak:can_speak":
                return [False]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        response = self.request(
            "/",
            method="POST",
            statement="hello"
        )

        self.assertEqual(response.code, 202)

    @mock.patch("cherrypy.engine.publish")
    def test_not_muted(self, publish_mock):
        """Valid notifications trigger a speak event"""

        def side_effect(*args, **_):
            """Side effects local function"""

            if args[0] == "speak:can_speak":
                return [True]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        response = self.request(
            "/",
            method="POST",
            statement="hello not muted"
        )

        self.assertEqual(response.code, 204)

        self.assertEqual(
            publish_mock.call_args[0][1],
            "hello not muted"
        )


if __name__ == "__main__":
    unittest.main()
