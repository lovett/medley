from testing import assertions
from testing import cptestcase
from testing import helpers
import unittest
import apps.azure.main
import mock

class TestAzure(cptestcase.BaseCherryPyTestCase, assertions.ResponseAssertions):

    @classmethod
    def setUpClass(cls):
        helpers.start_server(apps.azure.main.Controller)

    @classmethod
    def tearDownClass(cls):
        helpers.stop_server()

    def test_allow(self):
        response = self.request("/", method="HEAD")
        self.assertAllowedMethods(response, ("POST",))

    def test_requiresSiteName(self):
        """The request body must specify a site name"""
        response = self.request("/", method="POST", json_body={
            "status": "success"
        })
        self.assertEqual(response.code, 400)

    @mock.patch("cherrypy.engine.publish")
    def test_sendsSuccessNotification(self, publishMock):
        """A success status triggers a success notification"""

        def side_effect(*args, **kwargs):
            if (args[0] == "registry:first_value"):
                return ["http://example.com/{}"]

        publishMock.side_effect = side_effect

        response = self.request("/", method="POST", json_body={
            "siteName": "azuretest",
            "status": "success",
            "complete": True
        })

        notification = publishMock.call_args[0][1]

        self.assertEqual(response.code, 204)
        self.assertEqual("Deployment to azuretest is complete", notification["title"])
        self.assertEqual("http://example.com/azuretest", notification["url"])

    @mock.patch("cherrypy.engine.publish")
    def test_sendsFailureNotification(self, publishMock):
        """A failed status triggers a failure notification"""

        def side_effect(*args, **kwargs):
            if (args[0] == "registry:first_value"):
                return ["http://example.com/{}"]

        publishMock.side_effect = side_effect

        response = self.request("/", method="POST", json_body={
            "siteName": "azuretest",
            "status": "failed",
            "complete": True
        })

        notification = publishMock.call_args[0][1]

        self.assertEqual(response.code, 204)
        self.assertEqual("Deployment to azuretest has failed", notification["title"])
        self.assertEqual("http://example.com/azuretest", notification["url"])

    @mock.patch("cherrypy.engine.publish")
    def test_sendsUnknownStatusNotification(self, publishMock):
        """A status that is neither failed nor success triggers sends an
        unknown status notification
        """

        def side_effect(*args, **kwargs):
            if (args[0] == "registry:first_value"):
                return ["http://example.com/{}"]

        publishMock.side_effect = side_effect

        response = self.request("/", method="POST", json_body={
            "siteName": "azuretest",
            "status": "unexpected value",
            "complete": True
        })

        notification = publishMock.call_args[0][1]

        self.assertEqual(response.code, 204)
        self.assertEqual("Deployment to azuretest has uncertain status", notification["title"])
        self.assertEqual("http://example.com/azuretest", notification["url"])

    @mock.patch("cherrypy.engine.publish")
    def test_skipsUrlIfPortalNotConfigured(self, publishMock):
        """A failed status triggers a failure notification"""

        def side_effect(*args, **kwargs):
            if (args[0] == "registry:first_value"):
                return [None]

        publishMock.side_effect = side_effect

        response = self.request("/", method="POST", json_body={
            "siteName": "azuretest",
            "status": "success",
            "complete": True
        })

        notification = publishMock.call_args[0][1]

        self.assertEqual(response.code, 204)
        self.assertNotIn("url", notification)


if __name__ == "__main__":
    unittest.main()
