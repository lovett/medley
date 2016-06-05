import cptestcase
import helpers
import unittest
import responses
import apps.registry.models
import apps.jenkins.main
import mock
import requests_mock

class TestJenkins(cptestcase.BaseCherryPyTestCase):

    notifier_config = [
        {"key": "notifier:url", "value": "http://example.com"},
        {"key": "notifier:username", "value": "testuser"},
        {"key": "notifier:password", "value": "testpass"}
    ]

    @classmethod
    def setUpClass(cls):
        helpers.start_server(apps.jenkins.main.Controller)


    @classmethod
    def tearDownClass(cls):
        helpers.stop_server()

    @classmethod
    def setUp(self):
        self.test_payload = {
            "name": "testjob",
            "url": "job/testjob/",
            "build": {
                "full_url": "http://example.com/job/testjob/1/",
                "number": 1,
                "phase": "COMPLETED",
                "status": "SUCCESS",
                "url": "job/testjob/1/",
                "scm": {
                    "url": "https://example.org/testjob.git",
                    "branch": "origin/master",
                    "commit": "1234567890"
                }
            }
        }


    def test_requiresJson(self):
        """The request body must post a JSON payload"""

        response = self.request("/", method="POST")
        self.assertEqual(response.code, 415)

        response = self.request("/", method="POST", json_body={
            "hello": "world"
        })
        self.assertNotEqual(response.code, 415)

    @requests_mock.Mocker()
    @mock.patch("apps.registry.models.Registry.search")
    def test_notifyCompletedSuccess(self, requestsMock, registrySearchMock):
        """A success payload triggers a success notification"""

        registrySearchMock.return_value = self.notifier_config

        requestsMock.register_uri("POST", "http://example.com")

        payload = self.test_payload

        response = self.request("/", method="POST", json_body=self.test_payload)

        notification = requestsMock.request_history[0]

        self.assertEqual(response.code, 200)
        self.assertTrue(requestsMock.called)
        self.assertTrue("Jenkins+build+testjob+has+completed" in notification.text)
        self.assertTrue("SUCCESS" in notification.text)

    @requests_mock.Mocker()
    @mock.patch("apps.registry.models.Registry.search")
    def test_notifyCompletedFail(self, requestsMock, registrySearchMock):
        """A failure payload triggers a success notification"""

        registrySearchMock.return_value = self.notifier_config

        requestsMock.register_uri("POST", "http://example.com")

        payload = self.test_payload
        payload["build"]["status"] = "FAILED"

        response = self.request("/", method="POST", json_body=payload)

        notification = requestsMock.request_history[0]

        self.assertEqual(response.code, 200)
        self.assertTrue(requestsMock.called)
        self.assertTrue("FAILED" in notification.text)



if __name__ == "__main__":
    unittest.main()
