"""Text-to-speech."""

import cherrypy


class Controller:
    """Dispatch application requests based on HTTP verb."""

    name = "Speak"
    exposed = True
    show_on_homepage = True

    @staticmethod
    @cherrypy.tools.negotiable()
    def GET(*_args, **_kwargs):
        """Present an interface for on-demand and scheduled muting of the
        application.

        """
        can_speak = cherrypy.engine.publish("speak:can_speak").pop()

        return {
            "html": ("speak.jinja.html", {
                "can_speak": can_speak
            })
        }

    @staticmethod
    @cherrypy.tools.capture()
    def POST(*_args, **kwargs):
        """Accept a piece of text for text-to-speech conversion"""

        statement = kwargs.get("statement")
        locale = kwargs.get("locale", "en-GB")
        gender = kwargs.get("gender", "Male")
        action = kwargs.get("action", None)

        announcements = cherrypy.engine.publish(
            "registry:search",
            "speak:announcement:*",
            as_dict=True,
            key_slice=2
        ).pop()

        can_speak = cherrypy.engine.publish("speak:can_speak").pop()

        if action == "toggle":
            action = "unmute"
            if can_speak:
                action = "mute"

        if action == "mute":
            cherrypy.engine.publish("speak:mute")

            if "mute" in announcements:
                cherrypy.engine.publish(
                    "speak",
                    announcements["mute"],
                    locale,
                    gender
                )

        if action == "unmute":
            cherrypy.engine.publish("speak:unmute")

            if "unmute" in announcements:
                cherrypy.engine.publish(
                    "speak",
                    announcements["unmute"],
                    locale,
                    gender
                )

        if action:
            app_url = cherrypy.engine.publish(
                "url:internal"
            ).pop()

            raise cherrypy.HTTPRedirect(app_url)

        if not can_speak:
            response_status = 202
        else:
            cherrypy.engine.publish("speak", statement, locale, gender)
            response_status = 204

        cherrypy.response.status = response_status
