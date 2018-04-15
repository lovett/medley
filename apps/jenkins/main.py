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

    name = "Jenkins"

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

        if payload["status"].lower() == "failure":
            return False

        if payload["phase"].lower() == "completed":
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

        if phase == "started":
            title = "Jenkins is {} {}".format(action, name)

        if phase == "finalized":
            title = "Jenkins has finished {} {}".format(action, name)

        if status == "failure":
            title = "Jenkins had trouble {} {} ".format(action, name)
            group = "sysdown"

        return {
            "group": group,
            "badge": "jenkins.svg",
            "url": payload.get("url"),
            "localId": "jenkins.{}".format(payload["name"]),
            "title": title,
            "body": "Build #{}".format(payload["build_number"]),
        }

    @staticmethod
    def normalize_payload(payload):
        """Reshape an incoming payload to a standardized structure"""

        result = {}

        formats = {
            # Jenkins notifier plugin (non-pipeline)
            "plugin": lambda p: "name" in p and "build" in p,

            # Custom (Jenkins pipeline)
            "pipeline": lambda p: p.get("format") == "pipeline"
        }

        matches = (
            name for name, callback
            in formats.items()
            if callback(payload)
        )

        kind = list(matches)[0]

        if kind == "plugin":
            result["name"] = payload.get("name")
            result["build_number"] = payload["build"].get("number")
            result["phase"] = payload["build"].get("phase")
            result["status"] = payload["build"].get("status")
            result["url"] = payload["build"].get("full_url")

            result["action"] = "building"
            if "mirror" in payload["build"].get("full_url").lower():
                result["action"] = "mirroring"

        if kind == "pipeline":
            result["name"] = payload.get("name")
            result["build_number"] = payload.get("build_number")
            result["phase"] = payload.get("phase")
            result["status"] = payload.get("status")
            result["url"] = payload.get("url")
            result["action"] = "building"

        return result
