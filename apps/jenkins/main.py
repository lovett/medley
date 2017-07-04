import time
import cherrypy
import requests
import apps.registry.models
import tools.capture

class Controller:
    """Relay deployment notifications from Jenkins

    This works with the Jenkins Notification Plugin:
    https://wiki.jenkins-ci.org/display/JENKINS/Notification+Plugin

    Each Jenkins job should specify this app's URL as a notification
    endpoint. All event types will be accepted, but the completed event
    will be silently dropped in favor of the finalized event to avoid
    double notification.

    The difference between the finalized and completed events is
    described at the URL above: "...[W]hen job is finalized all
    post-build activities, such as archiving artifacts, were executed
    as well. This is not the case with job being merely "completed"
    which usually involves only creation of job's artifacts without
    post-processing them."
    """

    name = "Jenkins"

    _cp_config = {
        'tools.conditional_auth.on': False
    }

    exposed = True

    user_facing = False

    @cherrypy.tools.json_in()
    @cherrypy.tools.capture()
    def POST(self):
        details = cherrypy.request.json

        registry = apps.registry.models.Registry()

        notifier_config = registry.search(key="notifier:*")
        if not notifier_config:
            raise cherrypy.HTTPError(
                500,
                "No notification config found in registry"
            )

        notifier = {}
        for item in notifier_config:
            k = item["key"].split(":")[1]
            notifier[k] = item["value"]

        notification = {
            "group": "jenkins",
            "url": details["build"]["full_url"],
            "localId": "jenkins.{}".format(details["name"])
        }

        if details["build"]["phase"].lower() == "completed":
            # Disregard completed events to avoid double-notification with
            # finalized event (Jenkins is expected to send all supported
            # event types).
            cherrypy.response.status = 204
            return

        if details["build"]["phase"].lower() == "started":
            notification["title"] = "Starting a build for {}".format(details["name"])
            notification["body"] = "Build #{}".format(details["build"]["number"])

        if details["build"]["phase"].lower() == "finalized":
            if details["build"]["status"].lower() == "success":
                notification["title"] = "Jenkins has finished building {}".format(
                    details["name"],
                )
                notification["body"] = "Build #{}".format(details["build"]["number"])
            else:
                notification["title"] = "Jenkins had trouble with {} ".format(
                    details["name"]
                )

                notification["body"] = "Status: {}".format(
                    details["build"]["status"]
                )

        r = requests.post(
            notifier["url"],
            auth=(notifier["username"], notifier["password"]),
            data=notification
        )

        r.raise_for_status()
