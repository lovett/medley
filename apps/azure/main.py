import time
import cherrypy
import requests
import apps.registry.models
import tools.capture

class Controller:
    """Relay deployment notifications from Azure"""

    exposed = True

    user_facing = False

    url_template = "https://manage.windowsazure.com/@exampleUserId#Workspaces/WebsiteExtension/Website/{}/deployments"

    @cherrypy.tools.json_in()
    @cherrypy.tools.capture()
    def POST(self):
        registry = apps.registry.models.Registry()
        config = registry.search(key="notifier:*")
        notifier = {}

        if not config:
            raise cherrypy.HTTPError(500, "No configuration found in registry")

        for item in config:
            k = item["key"].split(":")[1]
            notifier[k] = item["value"]

        details = cherrypy.request.json

        if not details.get("siteName"):
            raise cherrypy.HTTPError(400, "Site name not specified")

        notification = {
            "group": "azure",
            "url": self.url_template.format(details["siteName"]),
            "body": details.get("message", "").split("\n")[0],
            "title": "Deployment to {}".format(details["siteName"])
        }

        if details.get("status") == "success" and details.get("complete") == True:
            notification["title"] += " is complete"
        elif details.get("status") == "failed":
            notification["title"] += " has failed"
        else:
            notification["title"] += " is {}".format(details.get("status", "not specified"))

        r = requests.post(notifier["url"], auth=(notifier["username"], notifier["password"]), data=notification)
        r.raise_for_status()
