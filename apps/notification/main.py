import cherrypy

class Controller:
    """Relay messages from notifier to the speech plugin"""

    name = "Notification"

    _cp_config = {
        'tools.conditional_auth.on': False
    }

    exposed = True

    user_facing = False

    @cherrypy.tools.capture()
    @cherrypy.tools.json_in()
    def POST(self):
        """Decide whether a notification is speakable.

        Disregard retractions, because they are not actionable here.
        """

        notification = cherrypy.request.json

        if "retracted" in notification:
            cherrypy.response.status = 204
            return

        if notification.get("group") == "reminder":
            cherrypy.response.status = 204
            return

        title = notification.get("title")

        if not title:
            cherrypy.response.status = 400
            return

        can_speak = cherrypy.engine.publish("speak:can_speak").pop()

        if not can_speak:
            response_status = 202
        else:
            cherrypy.engine.publish("speak", title)
            response_status = 204

        cherrypy.response.status = response_status
