"""Relay deployment notifications from Jenkins.

This works with the Jenkins Notification Plugin:
https://wiki.jenkins-ci.org/display/JENKINS/Notification+Plugin

It can also accept custom formats.

Each Jenkins job should specify this app's URL as a notification
endpoint. The app will determine whether to relay the notification
or drop it.

For notifications from the Jenkins Notification plugin, all event
local_types will be accepted but the completed event will be silently
dropped. The finalized event is favored instead to avoid double
notifications.

From the plugin documentation: "...[W]hen job is finalized all
post-build activities, such as archiving artifacts, were executed
as well. This is not the case with job being merely "completed"
which usually involves only creation of job's artifacts without
post-processing them."

"""

from collections import defaultdict
import cherrypy


class Controller:
    """Dispatch application requests based on HTTP verb."""

    exposed = True
    user_facing = False

    @cherrypy.tools.json_in()
    @cherrypy.tools.capture()
    def POST(self):
        """Receive a JSON payload from Jenkins"""

        payload = self.normalize_payload(cherrypy.request.json)

        if payload["send_notification"] is False:
            cherrypy.response.status = 202
            return

        notification = self.build_notification(payload)

        if notification.title:
            cherrypy.engine.publish(
                "notifier:send",
                notification
            )

        cherrypy.response.status = 204

    @staticmethod
    def build_notification(payload):
        """
        Transform a normalized Jenkins payload into a notification.
        """

        phase = payload.get("phase")
        status = payload.get("status")
        name = payload.get("name")
        action = payload.get("action")
        group = "sysup"
        url = payload.get("jenkins_url")
        title = None
        build_number = payload.get("build_number")
        branch = payload.get("branch")

        if phase == "queued":
            title = f"Jenkins has queued {name} for {action}"

        if phase == "started":
            title = f"Jenkins is {action} {name}"

        # When a job finishes successfully, link to the corresponding
        # site if known and fall back to the Jenkins URL if not.
        if phase == "finalized" and status == "success":
            title = f"Jenkins has finished {action} {name}"
            url = payload.get("site_url", url)

        # When a job fails, always link back to the Jenkins URL.
        if phase == "finalized" and status == "failure":
            group = "sysdown"
            title = f"Jenkins had trouble {action} {name}"

        return cherrypy.engine.publish(
            "notifier:build",
            group=group,
            badge="jenkins.svg",
            url=url,
            localId=f"jenkins.{payload['name']}",
            title=title,
            body=f"Build #{build_number}, {branch}"
        ).pop()

    @staticmethod
    def normalize_payload(raw_payload):
        """Reshape an incoming payload to a flatter structure."""

        def empty_string():
            """Initial value for defaultdict default_factory."""
            return ""

        build = defaultdict(
            empty_string,
            raw_payload.get("build", ())
        )

        scm = defaultdict(
            empty_string,
            build.get("scm", ())
        )

        result = defaultdict(empty_string)

        result["name"] = raw_payload.get("name").lower()
        result["build_number"] = build["number"]
        result["phase"] = build["phase"].lower()
        result["status"] = build["status"].lower()
        result["branch"] = scm["branch"].split("/", 1).pop()
        result["commit"] = scm["commit"]
        result["repository_url"] = scm["url"]

        result["jenkins_url"] = build["full_url"].rstrip("/") + "/console"

        result["site_url"] = cherrypy.engine.publish(
            "registry:first_value",
            f"site_url:{result['name']}:{result['branch']}"
        ).pop()

        if "mirror" in build.get("full_url").lower():
            result["action"] = "mirroring"
        else:
            result["action"] = "building"

        result["send_notification"] = True

        # Don't notify if the build is considered skippable.
        skippable_builds = cherrypy.engine.publish(
            "registry:search",
            "jenkins:skip",
            as_value_list=True
        ).pop()

        if result["name"] in skippable_builds:
            result["send_notification"] = False

        # Don't notify about queued builds.
        if result["phase"] == "queued":
            result["send_notification"] = False

        # Don't notify about completed builds. Wait for finalization instead.
        if result["phase"] == "completed":
            result["send_notification"] = False

        # Always notify about failed builds.
        if result["status"] == "failure":
            result["send_notification"] = True

        return result
