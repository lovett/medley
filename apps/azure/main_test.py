"""Test suite for the azure app"""

import unittest
import mock
from testing.assertions import ResponseAssertions
from testing import helpers
from testing.cptestcase import BaseCherryPyTestCase
import apps.azure.main


class TestAzure(BaseCherryPyTestCase, ResponseAssertions):
    """Tests for the azure application controller."""

    @classmethod
    def setUpClass(cls):
        """Start a faux cherrypy server"""
        helpers.start_server(apps.azure.main.Controller)

    @classmethod
    def tearDownClass(cls):
        """Shut down the faux server"""
        helpers.stop_server()

    def test_allow(self):
        """Verify the controller's supported HTTP methods"""
        response = self.request("/", method="HEAD")
        self.assertAllowedMethods(response, ("POST",))

    def test_requires_site_name(self):
        """The request body must specify a site name"""
        response = self.request("/", method="POST", json_body={
            "status": "success"
        })
        self.assertEqual(response.code, 400)

    @mock.patch("cherrypy.engine.publish")
    def test_sends_success_notification(self, publish_mock):
        """A success status triggers a success notification"""

        def side_effect(*args, **_):
            """Side effects local function"""
            if args[0] == "registry:first_value":
                return ["http://example.com/{}"]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        response = self.request("/", method="POST", json_body={
            "siteName": "azuretest",
            "status": "success",
            "complete": True
        })

        notification = publish_mock.call_args[0][1]

        self.assertEqual(response.code, 204)
        self.assertEqual(
            "Deployment to azuretest is complete",
            notification["title"]
        )

        self.assertEqual(
            "http://example.com/azuretest",
            notification["url"]
        )

    @mock.patch("cherrypy.engine.publish")
    def test_sends_failure_notification(self, publish_mock):
        """A failed status triggers a failure notification"""

        def side_effect(*args, **_):
            """Side effects local function"""
            if args[0] == "registry:first_value":
                return ["http://example.com/{}"]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        response = self.request("/", method="POST", json_body={
            "siteName": "azuretest",
            "status": "failed",
            "complete": True
        })

        notification = publish_mock.call_args[0][1]

        self.assertEqual(response.code, 204)
        self.assertEqual(
            "Deployment to azuretest has failed",
            notification["title"]
        )

        self.assertEqual(
            "http://example.com/azuretest",
            notification["url"]
        )

    @mock.patch("cherrypy.engine.publish")
    def test_sends_unknown_status(self, publish_mock):
        """A status that is neither failed nor success triggers sends an
        unknown status notification
        """

        def side_effect(*args, **_):
            """Side effects local function"""
            if args[0] == "registry:first_value":
                return ["http://example.com/{}"]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        response = self.request("/", method="POST", json_body={
            "siteName": "azuretest",
            "status": "unexpected value",
            "complete": True
        })

        notification = publish_mock.call_args[0][1]

        self.assertEqual(response.code, 204)
        self.assertEqual(
            "Deployment to azuretest has uncertain status",
            notification["title"]
        )

        self.assertEqual(
            "http://example.com/azuretest",
            notification["url"]
        )

    @mock.patch("cherrypy.engine.publish")
    def test_skips_url_if_no_portal(self, publish_mock):
        """A failed status triggers a failure notification"""

        def side_effect(*args, **_):
            """Side effects local function"""
            if args[0] == "registry:first_value":
                return [None]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        response = self.request("/", method="POST", json_body={
            "siteName": "azuretest",
            "status": "success",
            "complete": True
        })

        notification = publish_mock.call_args[0][1]

        self.assertEqual(response.code, 204)
        self.assertNotIn("url", notification)


if __name__ == "__main__":
    unittest.main()
