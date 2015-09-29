import sys
import os.path
sys.path.append("../../")

import time
import cherrypy
import util.net

class Controller:
    """Relay deployment notifications from Azure"""

    exposed = True

    user_facing = False

    url_template = "https://manage.windowsazure.com/@exampleUserId#Workspaces/WebsiteExtension/Website/{}/deployments"

    @cherrypy.tools.json_in()
    #@cherrypy.tools.capture()
    def POST(self):
        notifier = cherrypy.config.get("notifier")

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

        util.net.sendNotification(notification, notifier)
