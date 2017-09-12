from testing import assertions
from testing import cptestcase
from testing import helpers
import apps.notification.main
import mock
import unittest

class TestHeaders(cptestcase.BaseCherryPyTestCase, assertions.ResponseAssertions):

    @classmethod
    def setUpClass(cls):
        helpers.start_server(apps.notification.main.Controller)

    @classmethod
    def tearDownClass(cls):
        helpers.stop_server()

    def test_allow(self):
        """Only POST requests are allowed"""
        response = self.request("/", method="HEAD")
        self.assertAllowedMethods(response, ("POST",))

    def test_requiresJson(self):
        """Request bodies must be JSON"""
        response = self.request("/", method="POST", hello="world")
        self.assertEqual(response.code, 415)

    def test_retraction(self):
        """Retractions are ignored"""
        fixture = {
            "retracted": [
                "123-456-789"
            ]
        }

        response = self.request(
            "/",
            method="POST",
            json_body=fixture
        )

        self.assertEqual(response.code, 204)

    def test_reminder(self):
        """Reminders are ignored"""
        fixture = {
            "group": "reminder",
        }

        response = self.request(
            "/",
            method="POST",
            json_body=fixture
        )

        self.assertEqual(response.code, 204)

    def test_noTitle(self):
        """Notifications without a title are ignored"""
        fixture = {
            "group": "test",
        }

        response = self.request(
            "/",
            method="POST",
            json_body=fixture
        )

        self.assertEqual(response.code, 400)

    @mock.patch("cherrypy.engine.publish")
    def test_muted(self, publishMock):
        """If the application is muted, responses are returned with 202"""

        fixture = {
            "group": "test",
            "title": "hello world",
        }

        def side_effect(*args, **kwargs):
            if args[0] == "speak:is_muted":
                return [True]

        publishMock.side_effect = side_effect

        response = self.request(
            "/",
            method="POST",
            json_body=fixture,
        )

        self.assertEqual(response.code, 202)

    @mock.patch("cherrypy.engine.publish")
    def test_notMuted(self, publishMock):
        """Valid notifications trigger a speak event"""

        fixture = {
            "group": "test",
            "title": "hello world",
        }

        def side_effect(*args, **kwargs):
            if args[0] == "speak:is_muted":
                return [False]

        publishMock.side_effect = side_effect

        response = self.request(
            "/",
            method="POST",
            json_body=fixture,
        )

        self.assertEqual(response.code, 204)

        self.assertEqual(publishMock.call_args[0][1], "hello world")


if __name__ == "__main__":
    unittest.main()
