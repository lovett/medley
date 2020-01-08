"""Relay deployment notifications from Azure to notifier."""

import cherrypy


class Controller:
    """Dispatch application requests based on HTTP verb."""

    exposed = True
    show_on_homepage = False

    @staticmethod
    @cherrypy.tools.json_in()
    @cherrypy.tools.capture()
    def POST() -> None:
        """Transform a deployment notification from Azure to a notification."""

        details = cherrypy.request.json

        if not details.get("siteName"):
            raise cherrypy.HTTPError(400, "Site name not specified")

        body = details.get("message", "").split("\n")

        azure_portal_url = cherrypy.engine.publish(
            "registry:first_value",
            "azure:portal_url"
        ).pop()

        url = None
        if azure_portal_url:
            url = azure_portal_url.format(details["siteName"])

        title = f"Deployment to {details['siteName']}"
        if details.get("status") == "success" and details.get("complete"):
            title += " is complete"
        elif details.get("status") == "failed":
            title += " has failed"
        else:
            title += " has uncertain status"

        notification = cherrypy.engine.publish(
            "notifier:build",
            group="azure",
            body=body,
            url=url,
            title=title
        ).pop()

        cherrypy.engine.publish("notifier:send", notification)

        cherrypy.response.status = 204
