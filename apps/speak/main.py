"""Text-to-speech service"""

import typing
import cherrypy


class Controller:
    """Dispatch application requests based on HTTP verb."""

    exposed = True
    show_on_homepage = True

    @staticmethod
    @cherrypy.tools.provides(formats=("html",))
    def GET(*_args: str, **_kwargs: str) -> bytes:
        """Present an interface for on-demand muting of the speech service."""

        muted = cherrypy.engine.publish("speak:muted").pop()

        muted_by_schedule = cherrypy.engine.publish(
            "speak:muted:scheduled"
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

        return typing.cast(
            bytes,
            cherrypy.engine.publish(
                "jinja:render",
                "apps/speak/speak.jinja.html",
                muted=muted,
                muted_by_schedule=muted_by_schedule,
                registry_url=registry_url,
                schedules=schedules
            ).pop()
        )

    @staticmethod
    @cherrypy.tools.capture()
    def POST(*_args: str, **kwargs: str) -> None:
        """Accept a piece of text for text-to-speech conversion"""

        statement = kwargs.get("statement")
        locale = kwargs.get("locale", "en-GB")
        gender = kwargs.get("gender", "Male")
        action = kwargs.get("action", None)
        confirm = kwargs.get("confirm")

        muted = cherrypy.engine.publish("speak:muted").pop()

        if action == "toggle":
            action = "unmute" if muted else "mute"

        if action == "mute":
            cherrypy.engine.publish("speak:mute")

        if action == "unmute":
            cherrypy.engine.publish("speak:unmute")

        if action:
            app_url = cherrypy.engine.publish(
                "url:internal"
            ).pop()

            raise cherrypy.HTTPRedirect(app_url)

        if muted:
            response_status = 202
        else:
            if confirm:
                cherrypy.engine.publish(
                    "audio:play:asset",
                    "attention"
                )

            cherrypy.engine.publish("speak", statement, locale, gender)
            response_status = 204

        cherrypy.response.status = response_status
