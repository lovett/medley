"""Relay deployment notifications from Jenkins.

This works with the Jenkins Notification Plugin:
https://wiki.jenkins-ci.org/display/JENKINS/Notification+Plugin

It can also accept custom formats.

Each Jenkins job should specify this app's URL as a notification
endpoint. The app will determine whether to relay the notification
or drop it.

For notifications from the Jenkins Notification plugin, all event
types will be accepted but the completed event will be silently
dropped. The finalized event is favored instead to avoid double
notifications.

From the plugin documentation: "...[W]hen job is finalized all
post-build activities, such as archiving artifacts, were executed
as well. This is not the case with job being merely "completed"
which usually involves only creation of job's artifacts without
post-processing them."

"""

import cherrypy


class Controller:
    """Dispatch application requests based on HTTP verb."""

    user_facing = False

    _cp_config = {
        'tools.conditional_auth.on': False
    }

    @cherrypy.tools.json_in()
    @cherrypy.tools.capture()
    def POST(self):
        """Receive a JSON payload from Jenkins"""

        payload = self.normalize_payload(cherrypy.request.json)

        if self.payload_is_skippable(payload):
            cherrypy.response.status = 202
            return

        cherrypy.engine.publish(
            "notifier:send",
            self.build_notification(payload),
        )

        cherrypy.response.status = 204

    @staticmethod
    def payload_is_skippable(payload):
        """Should the payload produce a notification?"""

        status = payload.get("status") or ""
        phase = payload.get("phase") or ""

        if status.lower() == "failure":
            return False

        if phase.lower() == "completed":
            return True

        skips = cherrypy.engine.publish(
            "registry:search",
            "jenkins:skip",
            as_value_list=True
        ).pop()

        return payload.get("name") in skips

    @staticmethod
    def build_notification(payload):
        """
        Transform a normalized Jenkins payload into a notification.
        """

        phase = payload["phase"].lower()
        status = payload["status"].lower()
        name = payload.get("name")
        group = "sysup"
        action = payload.get("action")
        url = payload.get("jenkins_url")

        if phase == "started":
            title = "Jenkins is {} {}".format(action, name)

        if phase == "finalized":
            title = "Jenkins has finished {} {}".format(action, name)
            url = payload.get("site_url", url)

        if status == "failure":
            title = "Jenkins had trouble {} {}".format(action, name)
            group = "sysdown"

        return {
            "group": group,
            "badge": "jenkins.svg",
            "url": url,
            "localId": "jenkins.{}".format(payload["name"]),
            "title": title,
            "body": "Build #{}, {}".format(
                payload.get("build_number"),
                payload.get("branch")
            ),
        }

    @staticmethod
    def normalize_payload(payload):
        """Reshape an incoming payload to a simpler, flatter structure"""

        result = {}

        build = payload.get("build", {})
        scm = build.get("scm", {})

        result["name"] = payload.get("name")
        result["build_number"] = build.get("number")
        result["phase"] = build.get("phase")
        result["status"] = build.get("status")
        result["branch"] = scm.get("branch", "").split("/", 1).pop()
        result["commit"] = scm.get("commit")
        result["repository_url"] = scm.get("url")

        result["jenkins_url"] = build.get("full_url", "") + "console"

        result["site_url"] = cherrypy.engine.publish(
            "registry:first_value",
            "site_url:{}:{}".format(result["name"], result["branch"])
        ).pop()

        result["action"] = "building"
        if "mirror" in build.get("full_url").lower():
            result["action"] = "mirroring"

        return result
