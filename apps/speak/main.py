"""Text-to-speech."""

import cherrypy


class Controller:
    """Dispatch application requests based on HTTP verb."""

    name = "Speak"

    @cherrypy.tools.negotiable()
    def GET(self):
        """Present an interface for on-demand and scheduled muting of the
        application.

        """
        app_url = cherrypy.engine.publish(
            "url:internal"
        ).pop()

        can_speak = cherrypy.engine.publish("speak:can_speak").pop()

        return {
            "html": ("speak.jinja.html", {
                "app_name": self.name,
                "app_url": app_url,
                "can_speak": can_speak
            })
        }

    @staticmethod
    @cherrypy.tools.capture()
    def POST(statement=None, locale="en-IE", gender="Male", **kwargs):
        """Accept a piece of text for text-to-speech conversion"""

        action = kwargs.get("action", None)
        if action == "mute":
            cherrypy.engine.publish("speak:mute")

        if action == "unmute":
            cherrypy.engine.publish("speak:unmute")

        if action:
            app_url = cherrypy.engine.publish(
                "url:internal"
            ).pop()

            raise cherrypy.HTTPRedirect(app_url)

        can_speak = cherrypy.engine.publish("speak:can_speak").pop()

        if not can_speak:
            response_status = 202
        else:
            cherrypy.engine.publish("speak", statement, locale, gender)
            response_status = 204

        cherrypy.response.status = response_status
