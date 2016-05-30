import cptestcase
import helpers
import unittest
import responses
import apps.registry.models
import apps.azure.main
import mock
import requests_mock

class TestAzure(cptestcase.BaseCherryPyTestCase):

    notifier_config = [
        {"key": "notifier:url", "value": "http://example.com"},
        {"key": "notifier:username", "value": "testuser"},
        {"key": "notifier:password", "value": "testpass"}
    ]

    site_name = "azuretest"

    @classmethod
    def setUpClass(cls):
        helpers.start_server(apps.azure.main.Controller)


    @classmethod
    def tearDownClass(cls):
        helpers.stop_server()

    def test_requiresSiteName(self):
        """The request body must specify a site name"""
        response = self.request("/", method="POST", json_body={
            "status": "success"
        })
        self.assertEqual(response.code, 400)

    @requests_mock.Mocker()
    @mock.patch("apps.registry.models.Registry.search")
    def test_sendsSuccessNotification(self, requestsMock, registrySearchMock):
        """A status of failed triggers a failure notification"""

        registrySearchMock.return_value = self.notifier_config

        requestsMock.register_uri("POST", "http://example.com")

        response = self.request("/", method="POST", json_body={
            "siteName": self.site_name,
            "status": "success",
            "complete": True
        })

        notification = requestsMock.request_history[0]

        self.assertEqual(response.code, 200)
        self.assertTrue(requestsMock.called)
        self.assertFalse("has+uncertain+status" in notification.text)
        self.assertFalse("has+failed" in notification.text)
        self.assertTrue("is+complete" in notification.text)
        self.assertTrue(self.site_name in notification.text)

    @requests_mock.Mocker()
    @mock.patch("apps.registry.models.Registry.search")
    def test_sendsFailureNotification(self, requestsMock, registrySearchMock):
        """A status of failed triggers a failure notification"""

        registrySearchMock.return_value = self.notifier_config

        requestsMock.register_uri("POST", "http://example.com")

        response = self.request("/", method="POST", json_body={
            "siteName": self.site_name,
            "status": "failed",
            "complete": True
        })

        notification = requestsMock.request_history[0]

        self.assertEqual(response.code, 200)
        self.assertTrue(requestsMock.called)
        self.assertFalse("has+uncertain+status" in notification.text)
        self.assertTrue("has+failed" in notification.text)
        self.assertFalse("is+complete" in notification.text)
        self.assertTrue(self.site_name in notification.text)


    @requests_mock.Mocker()
    @mock.patch("apps.registry.models.Registry.search")
    def test_sendsUnknownNotification(self, requestsMock, registrySearchMock):
        """An unknown status value triggers a notification"""

        registrySearchMock.return_value = self.notifier_config

        requestsMock.register_uri("POST", "http://example.com")

        response = self.request("/", method="POST", json_body={
            "siteName": self.site_name,
            "status": "unexpected value",
            "complete": True
        })

        notification = requestsMock.request_history[0]

        self.assertEqual(response.code, 200)
        self.assertTrue(requestsMock.called)
        self.assertTrue("has+uncertain+status" in notification.text)
        self.assertFalse("has+failed" in notification.text)
        self.assertFalse("is+complete" in notification.text)
        self.assertTrue(self.site_name in notification.text)



if __name__ == "__main__":
    unittest.main()
