from testing import cptestcase
from testing import helpers
import unittest
import apps.jenkins.main
import mock

class TestJenkins(cptestcase.BaseCherryPyTestCase):

    @classmethod
    def setUpClass(cls):
        helpers.start_server(apps.jenkins.main.Controller)

    @classmethod
    def tearDownClass(cls):
        helpers.stop_server()

    @classmethod
    def setUp(self):

        self.config_fixture = {
            "notifier:url": "http://example.com",
            "notifier:username": "testuser",
            "notifier:password": "testpass",
        }

        self.plugin_fixture = {
            "name": "testjob",
            "url": "job/testjob/",
            "build": {
                "full_url": "http://example.com/job/testjob/1/",
                "number": 1,
                "phase": "FINALIZED",
                "status": "SUCCESS",
                "url": "job/testjob/1/",
                "scm": {
                    "url": "https://example.org/testjob.git",
                    "branch": "origin/master",
                    "commit": "1234567890"
                }
            }
        }

        self.pipeline_fixture = {
            "format": "pipeline",
            "name": "testjob-pipeline",
            "build_number": 1,
            "phase": "completed",
            "status": "success",
            "url": "http://example.com/job/testjob-pipeline/1/"
        }

    def get_fixture(self, format, phase, status):
        if format == "plugin":
            fixture = self.plugin_fixture
            fixture["build"]["phase"] = phase.upper()
            fixture["build"]["status"] = status.upper()
        if format == "pipeline":
            fixture = self.pipeline_fixture
            fixture["phase"] = phase
            fixture["status"] = status

        return fixture

    def default_side_effect_callback(self, *args, **kwargs):
        if args[0] == "registry:search":
            if args[1] == "notifier:*":
                return [self.config_fixture]
            if args[1] == "jenkins:skip":
                return [["skippable"]]

    def test_rejectsHtml(self):
        """The request body must contain JSON"""

        response = self.request("/", method="POST")
        self.assertEqual(response.code, 415)

    @mock.patch("cherrypy.engine.publish")
    def test_acceptsPluginFinalizedSuccess(self, publishMock):
        """JSON bodies from the Jenkins Notification plugin are accepted"""

        payload_fixture = self.get_fixture("plugin", "finalized", "success")

        publishMock.side_effect = self.default_side_effect_callback

        response = self.request(
            "/",
            method="POST",
            json_body=payload_fixture,
        )

        self.assertEqual(response.code, 204)

    @mock.patch("cherrypy.engine.publish")
    def test_acceptsPipelineFormat(self, publishMock):
        """JSON bodies from the Jenkins Notification plugin are accepted"""

        payload_fixture = self.get_fixture("pipeline", "finalized", "success")

        publishMock.side_effect = self.default_side_effect_callback

        response = self.request(
            "/",
            method="POST",
            json_body=payload_fixture,
        )

        self.assertEqual(response.code, 204)


    @mock.patch("cherrypy.engine.publish")
    def test_acceptsPluginCompletedSuccess(self, publishMock):
        """JSON bodies from the Jenkins Notification plugin are accepted"""

        payload_fixture = self.get_fixture("plugin", "completed", "success")

        publishMock.side_effect = self.default_side_effect_callback

        response = self.request(
            "/",
            method="POST",
            json_body=payload_fixture,
        )

        self.assertEqual(response.code, 202)

    @mock.patch("cherrypy.engine.publish")
    def test_skippableByPhase(self, publishMock):
        """Skip logic consiers project name and phase"""
        payload_fixture = self.get_fixture("plugin", "started", "success")
        payload_fixture["name"] = "skippable"

        publishMock.side_effect = self.default_side_effect_callback

        response = self.request("/", method="POST", json_body=payload_fixture)

        self.assertEqual(response.code, 202)

    @mock.patch("cherrypy.engine.publish")
    def test_skippableByStatus(self, publishMock):
        """Skip logic consiers project name and status"""

        payload_fixture = self.get_fixture("plugin", "completed", "success")
        payload_fixture["name"] = "skippable"

        publishMock.side_effect = self.default_side_effect_callback

        response = self.request("/", method="POST", json_body=payload_fixture)

        self.assertEqual(response.code, 202)

    @mock.patch("cherrypy.engine.publish")
    def test_skippableButNotOnFail(self, publishMock):
        """Failure status supersedes skip logic"""

        payload_fixture = self.get_fixture("plugin", "started", "failure")
        payload_fixture["name"] = "skippable"

        publishMock.side_effect = self.default_side_effect_callback

        response = self.request("/", method="POST", json_body=payload_fixture)

        self.assertEqual(response.code, 204)


if __name__ == "__main__":
    unittest.main()
