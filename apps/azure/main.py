import time
import cherrypy
import requests
import apps.registry.models
import tools.capture

class Controller:
    """Relay deployment notifications from Azure"""

    name = "Azure"

    _cp_config = {
        'tools.conditional_auth.on': False
    }

    exposed = True

    user_facing = False

    @cherrypy.tools.json_in()
    @cherrypy.tools.capture()
    def POST(self):
        details = cherrypy.request.json

        if not details.get("siteName"):
            raise cherrypy.HTTPError(400, "Site name not specified")

        registry = apps.registry.models.Registry()

        notifier_config = registry.search(key="notifier:*")
        if not notifier_config:
            raise cherrypy.HTTPError(500, "No notification config found in registry")

        notifier = {}
        for item in notifier_config:
            k = item["key"].split(":")[1]
            notifier[k] = item["value"]

        notification = {
            "group": "azure",
            "body": details.get("message", "").split("\n")[0],
            "title": "Deployment to {}".format(details["siteName"])
        }

        azure_portal_url = registry.search(key="azure:portal_url")
        if azure_portal_url:
            notification["url"] = azure_portal_url[0]["value"].format(details["siteName"])

        if details.get("status") == "success" and details.get("complete") == True:
            notification["title"] += " is complete"
        elif details.get("status") == "failed":
            notification["title"] += " has failed"
        else:
            notification["title"] += " has uncertain status"

        r = requests.post(notifier["url"], auth=(notifier["username"], notifier["password"]), data=notification)
        r.raise_for_status()
