"""Text-to-speech."""

import cherrypy


class Controller:
    """Dispatch application requests based on HTTP verb."""

    exposed = True
    show_on_homepage = True

    @staticmethod
    @cherrypy.tools.provides(formats=("html",))
    def GET(*_args, **_kwargs) -> bytes:
        """Present an interface for on-demand muting of the speech service."""

        can_speak = cherrypy.engine.publish("speak:can_speak").pop()

        muted_by_schedule = cherrypy.engine.publish(
            "speak:muted_by_schedule"
        ).pop()

        schedules = cherrypy.engine.publish(
            "registry:search:valuelist",
            "speak:mute",
            exact=True,
        ).pop()

        registry_url = cherrypy.engine.publish(
            "url:internal",
            "/registry",
            {"q": "speak:mute"}
        ).pop()

        return cherrypy.engine.publish(
            "jinja:render",
            "speak.jinja.html",
            can_speak=can_speak,
            muted_by_schedule=muted_by_schedule,
            registry_url=registry_url,
            schedules=schedules
        ).pop()

    @staticmethod
    @cherrypy.tools.capture()
    def POST(*_args, **kwargs) -> None:
        """Accept a piece of text for text-to-speech conversion"""

        statement = kwargs.get("statement")
        locale = kwargs.get("locale", "en-GB")
        gender = kwargs.get("gender", "Male")
        action = kwargs.get("action", None)

        announcements = cherrypy.engine.publish(
            "registry:search:dict",
            "speak:announcement:*",
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
