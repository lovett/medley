"""Test suite for the azure app"""

import typing
import unittest
from unittest import mock
from testing.assertions import ResponseAssertions
from testing import helpers
from testing.cptestcase import BaseCherryPyTestCase
import apps.azure.main


class TestAzure(BaseCherryPyTestCase, ResponseAssertions):
    """
    Tests for the application controller.
    """

    @classmethod
    def setUpClass(cls) -> None:
        """Start a faux cherrypy server"""
        helpers.start_server(apps.azure.main.Controller)

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
        self.assert_exposed(apps.azure.main.Controller)

    def test_not_show_on_homepage(self) -> None:
        """The application is displayed in the homepage app."""
        self.assert_not_show_on_homepage(apps.azure.main.Controller)

    def test_requires_site_name(self) -> None:
        """The request body must specify a site name"""
        response = self.request("/", method="POST", json_body={
            "status": "success"
        })
        self.assertEqual(response.code, 400)

    @mock.patch("cherrypy.engine.publish")
    def test_sends_success_notification(
            self,
            publish_mock: mock.Mock
    ) -> None:
        """A success status triggers a success notification"""

        def side_effect(*args: str, **_: str) -> typing.Any:
            """Side effects local function"""
            if args[0] == "registry:first:value":
                return ["http://example.com/{}"]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        response = self.request("/", method="POST", json_body={
            "siteName": "azuretest",
            "status": "success",
            "complete": True
        })

        notification_call = helpers.find_publish_call(
            publish_mock,
            "notifier:build"
        )

        self.assertEqual(response.code, 204)

        self.assertEqual(
            "Deployment to azuretest is complete",
            notification_call[1].get("title")
        )

        self.assertEqual(
            "http://example.com/azuretest",
            notification_call[1].get("url")
        )

    @mock.patch("cherrypy.engine.publish")
    def test_sends_failure_notification(
            self,
            publish_mock: mock.Mock
    ) -> None:
        """A failed status triggers a failure notification"""

        def side_effect(*args: str, **_: str) -> typing.Any:
            """Side effects local function"""
            if args[0] == "registry:first:value":
                return ["http://example.com/{}"]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        response = self.request("/", method="POST", json_body={
            "siteName": "azuretest",
            "status": "failed",
            "complete": True
        })

        notification_call = helpers.find_publish_call(
            publish_mock,
            "notifier:build"
        )

        self.assertEqual(response.code, 204)
        self.assertEqual(
            "Deployment to azuretest has failed",
            notification_call[1].get("title")
        )

        self.assertEqual(
            "http://example.com/azuretest",
            notification_call[1].get("url")
        )

    @mock.patch("cherrypy.engine.publish")
    def test_sends_unknown_status(
            self,
            publish_mock: mock.Mock
    ) -> None:
        """A status that is neither failed nor success triggers sends an
        unknown status notification
        """

        def side_effect(*args: str, **_: str) -> typing.Any:
            """Side effects local function"""
            if args[0] == "registry:first:value":
                return ["http://example.com/{}"]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        response = self.request("/", method="POST", json_body={
            "siteName": "azuretest",
            "status": "unexpected value",
            "complete": True
        })

        notification_call = helpers.find_publish_call(
            publish_mock,
            "notifier:build"
        )

        self.assertEqual(response.code, 204)
        self.assertEqual(
            "Deployment to azuretest has uncertain status",
            notification_call[1].get("title")
        )

        self.assertEqual(
            "http://example.com/azuretest",
            notification_call[1].get("url")
        )

    @mock.patch("cherrypy.engine.publish")
    def test_skips_url_if_no_portal(
            self,
            publish_mock: mock.Mock
    ) -> None:
        """A failed status triggers a failure notification"""

        def side_effect(*args: str, **_: str) -> typing.Any:
            """Side effects local function"""
            if args[0] == "registry:first:value":
                return [None]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        response = self.request("/", method="POST", json_body={
            "siteName": "azuretest",
            "status": "success",
            "complete": True
        })

        notification_call = helpers.find_publish_call(
            publish_mock,
            "notifier:build"
        )

        self.assertEqual(response.code, 204)
        self.assertIsNone(notification_call[1]["url"])


if __name__ == "__main__":
    unittest.main()
