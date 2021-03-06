"""Test suite for the jenkins app."""

import typing
import unittest
from unittest import mock
from testing.assertions import ResponseAssertions
from testing import helpers
from testing.cptestcase import BaseCherryPyTestCase
import apps.jenkins.main

Fixture = typing.Dict[str, typing.Any]


class TestJenkins(BaseCherryPyTestCase, ResponseAssertions):
    """
    Tests for the application controller.
    """

    controller: apps.jenkins.main.Controller

    @classmethod
    def setUpClass(cls) -> None:
        """Start a faux cherrypy server"""
        helpers.start_server(apps.jenkins.main.Controller)
        cls.controller = apps.jenkins.main.Controller()

    @classmethod
    def tearDownClass(cls) -> None:
        """Shut down the faux server"""
        helpers.stop_server()

    def setUp(self) -> None:
        """Fixtures available to all tests"""

        self.started_fixture: Fixture = {
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

        self.queued_fixture: Fixture = {
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

        self.plugin_fixture: Fixture = {
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

        self.plugin_mirror_fixture: Fixture = {
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

    def get_fixture(
            self,
            kind: str,
            phase: str = "",
            status: str = ""
    ) -> typing.Dict[str, typing.Any]:
        """Select of the available fixtures based on its structure and
        values.

        """

        if kind == "plugin":
            fixture = self.plugin_fixture
            if phase:
                fixture["build"]["phase"] = phase.upper()

            if status:
                fixture["build"]["status"] = status.upper()

        if kind == "plugin_mirror":
            fixture = self.plugin_mirror_fixture

        return fixture

    @staticmethod
    def default_side_effect_callback(*args: str, **_: str) -> typing.Any:
        """
        The standard mock side effect function used by all tests
        """

        if args[0] == "registry:search":
            if args[1] == "jenkins:skip":
                return [["skippable"]]
        if args[0] == "registry:first:value":
            if args[1].startswith("site_url"):
                return [None]
        return mock.DEFAULT

    def test_allow(self) -> None:
        """Verify the controller's supported HTTP methods"""
        response = self.request("/", method="HEAD")
        self.assert_allowed(response, ("POST",))

    def test_exposed(self) -> None:
        """The application is publicly available."""
        self.assert_exposed(apps.jenkins.main.Controller)

    def test_not_show_on_homepage(self) -> None:
        """The application is not displayed in the homepage app."""
        self.assert_not_show_on_homepage(apps.jenkins.main.Controller)

    def test_rejects_html(self) -> None:
        """The request body must contain JSON"""

        response = self.request("/", method="POST")
        self.assertEqual(response.code, 415)

    @mock.patch("cherrypy.engine.publish")
    def test_plugin_finalized_success(self, publish_mock: mock.Mock) -> None:
        """JSON bodies from the Jenkins Notification plugin are accepted"""

        payload_fixture = self.get_fixture("plugin", "finalized", "success")

        def side_effect(*args: str, **_: str) -> typing.Any:
            """Side effects local function"""
            if args[0] == "notifier:build":
                return [{"title": "test"}]
            if args[0] == "registry:search":
                if args[1] == "jenkins:skip":
                    return [["skippable"]]
                if args[0] == "registry:first:value":
                    if args[1].startswith("site_url"):
                        return [None]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        response = self.request(
            "/",
            method="POST",
            json_body=payload_fixture,
        )

        notification_send_call = helpers.find_publish_call(
            publish_mock, 'notifier:send'
        )

        self.assertIsNotNone(notification_send_call)
        self.assertEqual(notification_send_call[0][1]["title"], "test")
        self.assertEqual(response.code, 204)

    @mock.patch("cherrypy.engine.publish")
    def test_plugin_finalized_skip_send(self, publish_mock: mock.Mock) -> None:
        """A notification is not sent if the title is missing."""

        payload_fixture = self.get_fixture("plugin", "finalized", "success")

        def side_effect(*args: str, **_: str) -> typing.Any:
            """Side effects local function"""
            if args[0] == "notifier:build":
                return [{}]
            if args[0] == "registry:search":
                if args[1] == "jenkins:skip":
                    return [["skippable"]]
                if args[0] == "registry:first:value":
                    if args[1].startswith("site_url"):
                        return [None]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        response = self.request(
            "/",
            method="POST",
            json_body=payload_fixture,
        )

        notification_send_call = helpers.find_publish_call(
            publish_mock, 'notifier:send'
        )

        self.assertIsNone(notification_send_call)
        self.assertEqual(response.code, 204)

    @mock.patch("cherrypy.engine.publish")
    def test_plugin_completed_success(self, publish_mock: mock.Mock) -> None:
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
    def test_skippable_by_status(self, publish_mock: mock.Mock) -> None:
        """Skip logic considers project name and status"""

        payload_fixture = self.get_fixture("plugin", "completed", "success")
        payload_fixture["name"] = "skippable"

        publish_mock.side_effect = self.default_side_effect_callback

        response = self.request("/", method="POST", json_body=payload_fixture)

        self.assertEqual(response.code, 202)

    @mock.patch("cherrypy.engine.publish")
    def test_skippable_but_not_on_fail(self, publish_mock: mock.Mock) -> None:
        """Failure status supersedes skip logic"""

        payload_fixture = self.get_fixture("plugin", "started", "failure")
        payload_fixture["name"] = "skippable"

        publish_mock.side_effect = self.default_side_effect_callback

        response = self.request("/", method="POST", json_body=payload_fixture)

        self.assertEqual(response.code, 204)

    @mock.patch("cherrypy.engine.publish")
    def test_build_action(self, publish_mock: mock.Mock) -> None:
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
    def test_queued(self, publish_mock: mock.Mock) -> None:
        """A notification is sent when the build is queued."""

        publish_mock.side_effect = self.default_side_effect_callback

        fixture = self.queued_fixture
        payload = self.controller.normalize_payload(fixture)

        self.controller.build_notification(payload)

        notification_call = helpers.find_publish_call(
            publish_mock,
            "notifier:build"
        )

        self.assertIn("has queued", notification_call[1].get("title"))
        self.assertIn("for building", notification_call[1].get("title"))

    @mock.patch("cherrypy.engine.publish")
    def test_started(self, publish_mock: mock.Mock) -> None:
        """A notification is sent when the build is started."""

        publish_mock.side_effect = self.default_side_effect_callback

        fixture = self.started_fixture
        payload = self.controller.normalize_payload(fixture)

        self.controller.build_notification(payload)

        notification_call = helpers.find_publish_call(
            publish_mock,
            "notifier:build"
        )

        self.assertIn("is building", notification_call[1].get("title"))


if __name__ == "__main__":
    unittest.main()
