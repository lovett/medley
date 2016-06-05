import time
import cherrypy
import requests
import apps.registry.models
import tools.capture

class Controller:
    """Relay deployment notifications from Jenkins"""

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
            raise cherrypy.HTTPError(500, "No notification config found in registry")

        notifier = {}
        for item in notifier_config:
            k = item["key"].split(":")[1]
            notifier[k] = item["value"]

        notification = {
            "group": "jenkins",
            "url": details["build"]["full_url"]
        }

        # Phase can be STARTED, COMPLETED, or FINALIZED
        notification["title"] = "Jenkins build {} has {}".format(details["name"], details["build"]["phase"].lower())
        notification["body"] = "Status: {}".format(details["build"]["status"])

        r = requests.post(notifier["url"], auth=(notifier["username"], notifier["password"]), data=notification)
        r.raise_for_status()
