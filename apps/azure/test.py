import cptestcase
import helpers
import unittest
import responses
import apps.azure.main
import mock
import util.net

class TestTopics(cptestcase.BaseCherryPyTestCase):
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
        print(response.body)
        self.assertEqual(response.code, 400)

    @mock.patch("util.net.sendNotification")
    def test_sendsSuccessNotification(self, sendNotificationMock):
        """The request body must specify a site name"""
        site_name = "test"
        response = self.request("/", method="POST", json_body={
            "siteName": site_name,
            "status": "success",
            "complete": True
        })

        notification = sendNotificationMock.call_args[0][0]

        self.assertEqual(response.code, 200)
        self.assertTrue("is complete" in notification["title"])
        self.assertEqual(notification["group"], "azure")
        self.assertTrue(site_name in notification["url"])

    @mock.patch("util.net.sendNotification")
    def test_sendsFailureNotification(self, sendNotificationMock):
        """The request body must specify a site name"""
        site_name = "testfail"
        response = self.request("/", method="POST", json_body={
            "siteName": site_name,
            "status": "failed",
            "complete": True
        })

        notification = sendNotificationMock.call_args[0][0]

        self.assertEqual(response.code, 200)
        self.assertTrue("has failed" in notification["title"])
        self.assertFalse("is complete" in notification["title"])
        self.assertEqual(notification["group"], "azure")
        self.assertTrue(site_name in notification["url"])

    @mock.patch("util.net.sendNotification")
    def test_sendsUnknownNotification(self, sendNotificationMock):
        """The request body must specify a site name"""
        site_name = "testfail"
        response = self.request("/", method="POST", json_body={
            "siteName": site_name,
            "status": "unexpected value",
            "complete": True
        })

        notification = sendNotificationMock.call_args[0][0]

        self.assertEqual(response.code, 200)
        self.assertTrue("is unexpected value" in notification["title"])
        self.assertFalse("has failed" in notification["title"])
        self.assertFalse("is complete" in notification["title"])
        self.assertEqual(notification["group"], "azure")
        self.assertTrue(site_name in notification["url"])



if __name__ == "__main__":
    unittest.main()
