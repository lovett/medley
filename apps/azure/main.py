"""Relay deployment notifications from Azure to notifier."""

import cherrypy


class Controller:
    """Dispatch application requests based on HTTP verb."""

    user_facing = False

    @staticmethod
    @cherrypy.tools.json_in()
    @cherrypy.tools.capture()
    def POST():
        """Transform a deployment notification from Azure to a notification."""

        details = cherrypy.request.json

        if not details.get("siteName"):
            raise cherrypy.HTTPError(400, "Site name not specified")

        notification = {
            "group": "azure",
            "body": details.get("message", "").split("\n")[0],
            "title": "Deployment to {}".format(details["siteName"])
        }

        azure_portal_url = cherrypy.engine.publish(
            "registry:first_value",
            "azure:portal_url"
        ).pop()

        if azure_portal_url:
            notification["url"] = azure_portal_url.format(details["siteName"])

        if details.get("status") == "success" and details.get("complete"):
            notification["title"] += " is complete"
        elif details.get("status") == "failed":
            notification["title"] += " has failed"
        else:
            notification["title"] += " has uncertain status"

        cherrypy.engine.publish("notifier:send", notification)

        cherrypy.response.status = 204
