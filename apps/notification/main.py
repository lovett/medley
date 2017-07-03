import cherrypy
import apps.speak.models
import tools.capture

class Controller:
    """
    Relay messages from notifier to the speak app
    """

    name = "Notification"

    _cp_config = {
        'tools.conditional_auth.on': False
    }

    exposed = True

    user_facing = False

    @cherrypy.tools.json_in()
    @cherrypy.tools.capture()
    def POST(self):
        notification = cherrypy.request.json

        if "retracted" in notification:
            cherrypy.response.status = 204
            return

        title = notification.get("title")

        if not title:
            cherrypy.response.status = 400
            return

        manager = apps.speak.models.SpeechManager()
        manager.say(notification["title"], "en-GB", "Male")

        return
