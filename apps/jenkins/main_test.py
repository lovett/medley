"""
Test suite for the jenkins app
"""

import unittest
import mock
from testing.assertions import ResponseAssertions
from testing import helpers
from testing.cptestcase import BaseCherryPyTestCase
import apps.jenkins.main


class TestJenkins(BaseCherryPyTestCase, ResponseAssertions):
    """
    Tests for the application controller.
    """

    @classmethod
    def setUpClass(cls):
        """Start a faux cherrypy server"""
        helpers.start_server(apps.jenkins.main.Controller)
        cls.controller = apps.jenkins.main.Controller()

    @classmethod
    def tearDownClass(cls):
        """Shut down the faux server"""
        helpers.stop_server()

    def setUp(self):
        """Fixtures available to all tests"""

        self.config_fixture = {
            "notifier:url": "http://example.com",
            "notifier:username": "testuser",
            "notifier:password": "testpass",
        }

        self.started_fixture = {
            "name": "testjob",
            "url": "job/testjob/",
            "build": {
                "artifacts": {},
                "full_url": "http://example.com/job/testjob/1/",
                "log": "",
                "number": 1,
                "phase": "STARTED",
                "queue_id": 1,
                "scm": {
                    "branch": "origin/master",
                    "changes": [],
                    "commit": "1234567890",
                    "culprits": []
                },
                "timestamp": 1529681225640,
                "url": "job/testjob/1/"
            },
            "display_name": "testjob",
        }

        self.queued_fixture = {
            "name": "testjob",
            "url": "job/testjob/",
            "build": {
                "artifacts": {},
                "full_url": "http://example.com/job/testjob/1/",
                "log": "",
                "number": 1,
                "phase": "QUEUED",
                "queue_id": 1,
                "scm": {
                    "branch": "origin/master",
                    "changes": [],
                    "commit": "1234567890",
                    "culprits": []
                },
                "timestamp": 1529681225640,
                "url": "job/testjob/1/"
            },
            "display_name": "testjob",
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

        self.plugin_mirror_fixture = {
            "name": "test",
            "url": "job/mirror/test/",
            "build": {
                "full_url": "http://example.com/job/mirror/test/1/",
                "number": 1,
                "phase": "FINALIZED",
                "status": "SUCCESS",
                "url": "job/mirror/test/1/",
                "scm": {
                    "url": "https://example.org/mirror/test.git",
                    "branch": "origin/master",
                    "commit": "1234567890"
                }
            }
        }

    def get_fixture(self, kind, phase=None, status=None):
        """
        Select of the available fixtures based on its structure and
        values
        """

        if kind == "plugin":
            fixture = self.plugin_fixture
            fixture["build"]["phase"] = phase.upper()
            fixture["build"]["status"] = status.upper()
        if kind == "plugin_mirror":
            fixture = self.plugin_mirror_fixture

        return fixture

    def default_side_effect_callback(self, *args, **_):
        """
        The standard mock side effect function used by all tests
        """

        if args[0] == "registry:search":
            if args[1] == "notifier:*":
                return [self.config_fixture]
            if args[1] == "jenkins:skip":
                return [["skippable"]]
        if args[0] == "registry:first_value":
            if args[1].startswith("site_url"):
                return [None]
        return mock.DEFAULT

    def test_allow(self):
        """Verify the controller's supported HTTP methods"""
        response = self.request("/", method="HEAD")
        self.assert_allowed(response, ("POST",))

    def test_exposed(self):
        """The application is publicly available."""
        self.assert_exposed(apps.jenkins.main.Controller)

    def test_not_user_facing(self):
        """The application is not displayed in the homepage app."""
        self.assert_not_user_facing(apps.jenkins.main.Controller)

    def test_rejects_html(self):
        """The request body must contain JSON"""

        response = self.request("/", method="POST")
        self.assertEqual(response.code, 415)

    @mock.patch("cherrypy.engine.publish")
    def test_plugin_finalized_success(self, publish_mock):
        """JSON bodies from the Jenkins Notification plugin are accepted"""

        payload_fixture = self.get_fixture("plugin", "finalized", "success")

        publish_mock.side_effect = self.default_side_effect_callback

        response = self.request(
            "/",
            method="POST",
            json_body=payload_fixture,
        )

        self.assertEqual(response.code, 204)

    @mock.patch("cherrypy.engine.publish")
    def test_plugin_completed_success(self, publish_mock):
        """JSON bodies from the Jenkins Notification plugin are accepted"""

        payload_fixture = self.get_fixture("plugin", "completed", "success")

        publish_mock.side_effect = self.default_side_effect_callback

        response = self.request(
            "/",
            method="POST",
            json_body=payload_fixture,
        )

        self.assertEqual(response.code, 202)

    @mock.patch("cherrypy.engine.publish")
    def test_skippable_by_status(self, publish_mock):
        """Skip logic considers project name and status"""

        payload_fixture = self.get_fixture("plugin", "completed", "success")
        payload_fixture["name"] = "skippable"

        publish_mock.side_effect = self.default_side_effect_callback

        response = self.request("/", method="POST", json_body=payload_fixture)

        self.assertEqual(response.code, 202)

    @mock.patch("cherrypy.engine.publish")
    def test_skippable_but_not_on_fail(self, publish_mock):
        """Failure status supersedes skip logic"""

        payload_fixture = self.get_fixture("plugin", "started", "failure")
        payload_fixture["name"] = "skippable"

        publish_mock.side_effect = self.default_side_effect_callback

        response = self.request("/", method="POST", json_body=payload_fixture)

        self.assertEqual(response.code, 204)

    @mock.patch("cherrypy.engine.publish")
    def test_build_action(self, publish_mock):
        """Payload normalization looks for keywords in the URL to describe the
        action that best fits the job.

        """

        publish_mock.side_effect = self.default_side_effect_callback

        payload_fixture = self.get_fixture("plugin_mirror")
        normalized_payload = self.controller.normalize_payload(
            payload_fixture
        )

        self.assertEqual(normalized_payload.get("action"), "mirroring")

    @mock.patch("cherrypy.engine.publish")
    def test_queued(self, publish_mock):
        """A notification is sent when the build is queued."""

        publish_mock.side_effect = self.default_side_effect_callback

        fixture = self.queued_fixture
        payload = self.controller.normalize_payload(fixture)
        notification = self.controller.build_notification(payload)

        self.assertIn("has queued", notification.get("title"))
        self.assertIn("for building", notification.get("title"))

    @mock.patch("cherrypy.engine.publish")
    def test_started(self, publish_mock):
        """A notification is sent when the build is started."""

        publish_mock.side_effect = self.default_side_effect_callback

        fixture = self.started_fixture
        payload = self.controller.normalize_payload(fixture)
        notification = self.controller.build_notification(payload)

        self.assertIn("is building", notification.get("title"))


if __name__ == "__main__":
    unittest.main()
