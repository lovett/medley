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
        """Decide whether a notification is speakable.

        Retractions are not, so respond with a 204. Likewise for
        reminders, which get the same treatment because they recur too
        frequently to be meaningful."""

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

        manager = apps.speak.models.SpeechManager()

        if manager.isMuted():
            cherrypy.response.status = 202
            return

        manager.say(title, "en-GB", "Male")

        return
